"""最小工具层：注册表 + 输入输出校验 + 超时/重试 + 结构化日志。

设计约束（来自最小改动指令）：
- 每个工具有 Pydantic 输入输出、统一错误码、超时与重试；
- 默认只读；写类工具（建工单）只做本地副作用，不触发真实系统；
- 工具通过 ToolContext 注入依赖，测试可替换为假实现。
"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("rag.tools")

# 工具超时与重试允许用环境变量调整，默认值与最小改动指令一致。
DEFAULT_TOOL_TIMEOUT_SECONDS = float(os.getenv("TOOL_TIMEOUT_SECONDS", "3"))
DEFAULT_TOOL_MAX_RETRIES = int(os.getenv("TOOL_MAX_RETRIES", "1"))


class ToolErrorCode:
    """统一错误码，工具与工作流共用。"""

    OK = "OK"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INTERNAL = "INTERNAL"


RETRYABLE_CODES = {ToolErrorCode.UPSTREAM_TIMEOUT, ToolErrorCode.INTERNAL}


@dataclass
class ToolContext:
    """工具运行时上下文：租户、会话与检索/生成依赖都在这里注入。"""

    tenant_id: str = "default"
    session_id: str | None = None
    pipeline: Any | None = None
    exclude_sources: set[str] | None = None


class ToolResult(BaseModel):
    ok: bool
    code: str = ToolErrorCode.OK
    data: Any | None = None
    error: str | None = None
    duration_ms: int = 0
    attempts: int = 1
    retryable: bool = False


class KnowledgeSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class OrderLookupInput(BaseModel):
    order_id: str = Field(min_length=4, max_length=40)


class LogisticsTrackInput(BaseModel):
    order_id: str = Field(min_length=4, max_length=40)


class HumanHandoffInput(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    reason: Literal[
        "complaint",
        "insufficient_context",
        "user_request",
        "tool_failure",
        "unsafe_request",
    ] = "user_request"


@dataclass
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[BaseModel, ToolContext], ToolResult]
    timeout_seconds: float = DEFAULT_TOOL_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_TOOL_MAX_RETRIES
    permission: Literal["read", "write"] = "read"
    side_effect: bool = False


TOOL_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(spec: ToolSpec) -> None:
    TOOL_REGISTRY[spec.name] = spec


def get_tool_spec(name: str) -> ToolSpec | None:
    return TOOL_REGISTRY.get(name)


def list_tool_names() -> list[str]:
    return sorted(TOOL_REGISTRY)


def _log(event: dict) -> None:
    """结构化日志：一行一个 JSON，便于离线分析。"""
    logger.info(json.dumps({"event": "tool_call", **event}, ensure_ascii=False))


def _run_with_timeout(
    spec: ToolSpec,
    payload: BaseModel,
    context: ToolContext,
    timeout_seconds: float | None = None,
) -> ToolResult:
    # 用线程池给同步工具加真实超时；超时视为可重试的上游问题。
    limit = spec.timeout_seconds if timeout_seconds is None else timeout_seconds
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(spec.handler, payload, context)
        try:
            return future.result(timeout=limit)
        except FutureTimeoutError:
            return ToolResult(
                ok=False,
                code=ToolErrorCode.UPSTREAM_TIMEOUT,
                error=f"{spec.name} 超时（>{limit}s）",
                retryable=True,
            )
        except Exception as exc:  # 工具内部异常不能打断整个工作流
            return ToolResult(
                ok=False,
                code=ToolErrorCode.INTERNAL,
                error=f"{spec.name} 内部错误：{type(exc).__name__}",
                retryable=True,
            )


def execute_tool(
    name: str,
    payload: dict,
    context: ToolContext,
    max_retries: int | None = None,
    timeout_seconds: float | None = None,
) -> ToolResult:
    """校验参数 → 带超时执行 → 失败按策略重试 → 记录结构化日志。"""
    started = time.perf_counter()
    spec = get_tool_spec(name)
    if spec is None:
        return ToolResult(
            ok=False,
            code=ToolErrorCode.INVALID_ARGUMENT,
            error=f"未知工具：{name}",
        )

    try:
        parsed = spec.input_model.model_validate(payload)
    except ValidationError as exc:
        result = ToolResult(
            ok=False,
            code=ToolErrorCode.INVALID_ARGUMENT,
            error=f"参数校验失败：{exc.error_count()} 处",
        )
        _log({"tool": name, "code": result.code, "attempts": 1})
        return result

    retries = spec.max_retries if max_retries is None else max_retries
    result = ToolResult(ok=False, code=ToolErrorCode.INTERNAL, error="未执行")
    attempts = 0

    for attempt in range(retries + 1):
        attempts = attempt + 1
        result = _run_with_timeout(spec, parsed, context, timeout_seconds=timeout_seconds)
        result.attempts = attempts
        if result.ok or not result.retryable:
            break

    result.duration_ms = int((time.perf_counter() - started) * 1000)
    _log(
        {
            "tool": name,
            "code": result.code,
            "attempts": attempts,
            "duration_ms": result.duration_ms,
            "permission": spec.permission,
        }
    )
    return result


def _knowledge_search(payload: KnowledgeSearchInput, context: ToolContext) -> ToolResult:
    if context.pipeline is None:
        return ToolResult(ok=False, code=ToolErrorCode.INTERNAL, error="检索管线未注入")

    contexts = context.pipeline.retrieve(
        payload.query,
        top_k=payload.top_k,
        exclude_sources=context.exclude_sources,
        tenant_id=context.tenant_id,
    )
    evidence = [
        {
            "id": item.metadata.get("id") or item.metadata.get("source", "unknown"),
            "text": item.text,
            "source": item.metadata.get("source", "未知来源"),
            "score": round(float(item.combined_score), 4),
            "raw_dense_score": round(float(item.raw_dense_score), 4),
        }
        for item in contexts
    ]
    return ToolResult(ok=True, data={"count": len(evidence), "evidence": evidence})


def _order_lookup(payload: OrderLookupInput, context: ToolContext) -> ToolResult:
    from .order_store import find_order, mask_phone

    order = find_order(payload.order_id, tenant_id=context.tenant_id)
    if order is None:
        return ToolResult(
            ok=False,
            code=ToolErrorCode.NOT_FOUND,
            error=f"未找到订单 {payload.order_id}",
        )

    order["receiver_phone"] = mask_phone(order.get("receiver_phone"))
    return ToolResult(ok=True, data={"order": order})


def _logistics_track(payload: LogisticsTrackInput, context: ToolContext) -> ToolResult:
    from .order_store import find_logistics

    record = find_logistics(payload.order_id, tenant_id=context.tenant_id)
    if record is None:
        return ToolResult(
            ok=False,
            code=ToolErrorCode.NOT_FOUND,
            error=f"未找到订单 {payload.order_id} 的物流信息",
        )
    return ToolResult(ok=True, data={"logistics": record})


def _human_handoff(payload: HumanHandoffInput, context: ToolContext) -> ToolResult:
    from .ticket_store import create_ticket

    ticket = create_ticket(
        question=payload.question,
        session_id=context.session_id,
        reason=payload.reason,
        tenant_id=context.tenant_id,
    )
    return ToolResult(
        ok=True,
        data={
            "ticket_id": ticket["id"],
            "reason": ticket["reason"],
            "status": ticket["status"],
        },
    )


register_tool(
    ToolSpec(
        name="knowledge_search",
        description="在企业知识库中做混合检索，返回带引用的证据片段。",
        input_model=KnowledgeSearchInput,
        handler=_knowledge_search,
        timeout_seconds=3.0,
    )
)

register_tool(
    ToolSpec(
        name="order_lookup",
        description="按订单号查询订单状态、金额与商品，返回结果已做手机号脱敏。",
        input_model=OrderLookupInput,
        handler=_order_lookup,
        timeout_seconds=3.0,
    )
)

register_tool(
    ToolSpec(
        name="logistics_track",
        description="按订单号查询物流轨迹与最新状态。",
        input_model=LogisticsTrackInput,
        handler=_logistics_track,
        timeout_seconds=3.0,
    )
)

register_tool(
    ToolSpec(
        name="human_handoff",
        description="创建本地工单并转人工，是唯一带副作用的工具，只写本地数据。",
        input_model=HumanHandoffInput,
        handler=_human_handoff,
        timeout_seconds=3.0,
        permission="write",
        side_effect=True,
    )
)
