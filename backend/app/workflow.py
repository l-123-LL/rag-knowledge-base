"""最小工具工作流：意图路由 → FAQ → 工具调用 → 质量判断 → 回答或转人工。

约束（来自最小改动指令）：最多 3 次业务工具调用、同一工具最多重试 1 次、
总超时 15 秒；无合适工具时回退原有 RAG；低相关或连续失败转人工。
转人工是终止动作，不占用步骤预算，保证任何情况下都能兜底。
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from .cost import calculate_cost
from .faq_store import find_faq_answer
from .intent import classify_intent
from .retrieval import RetrievedChunk
from .schemas import Citation
from .tools import ToolContext, execute_tool
from .trace_store import new_trace_id, write_trace

ORDER_ID_PATTERN = re.compile(r"[A-Za-z]{2}\d{6,}")
DIGITS_PATTERN = re.compile(r"\d{6,}")
LOGISTICS_KEYWORDS = ("物流", "快递", "包裹", "运单", "配送", "签收", "派送", "运输")
ORDER_KEYWORDS = ("订单", "下单", "发货", "什么时候发", "订单状态", "买了", "退款到哪")

# 多轮追问的指代线索：当前问题没带订单号、但仍在问订单/物流相关的事时，
# 回看最近几轮用户消息里出现过的订单号。（不含这些词的问题不会误复用。）
FOLLOW_UP_HINTS = (
    "它",
    "这个订单",
    "该订单",
    "那单",
    "那个订单",
    "订单",
    "物流",
    "快递",
    "包裹",
    "运单",
    "发货",
    "签收",
    "配送",
    "退款",
    "到哪",
    "状态",
    "进度",
    "多久",
    "什么时候",
    "还有",
)

# 最小输入护栏：命中这些模式直接转人工，避免提示词越权、密钥探测与跨租户尝试。
INJECTION_PATTERNS = (
    "忽略以上",
    "忽略之前",
    "忽略上述",
    "系统提示词",
    "system prompt",
    "你现在是管理员",
    "打印出来",
    "api_key",
    "apikey",
    "其他租户",
    "越狱",
    "jailbreak",
)

DEFAULT_MAX_STEPS = 3
DEFAULT_TOTAL_TIMEOUT_SECONDS = float(os.getenv("WORKFLOW_TOTAL_TIMEOUT_SECONDS", "15"))


@dataclass
class WorkflowOutcome:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    status: Literal["done", "insufficient"] = "done"
    trace_id: str = ""
    steps: list[dict] = field(default_factory=list)
    usage: dict[str, int] | None = None
    cost: float | None = None
    latency_ms: int = 0
    model: str = "workflow"
    tool_calls: int = 0
    handoff_reason: str | None = None


def extract_order_id(question: str) -> str | None:
    """从问题里抽取订单号：优先匹配 SO 前缀，其次匹配长数字。"""
    matched = ORDER_ID_PATTERN.search(question)
    if matched:
        return matched.group(0).upper()

    if any(keyword in question for keyword in ("订单", "物流", "快递")):
        digits = DIGITS_PATTERN.search(question)
        if digits:
            return digits.group(0)
    return None


def reuse_order_id_from_history(question: str, history: list[dict] | None) -> str | None:
    """多轮指代消解：从最近几轮用户消息里取上一个订单号。"""
    if not history:
        return None
    if not any(hint in question for hint in FOLLOW_UP_HINTS):
        return None

    for message in reversed(history[-6:]):
        if message.get("role") != "user":
            continue
        found = extract_order_id(str(message.get("content", "")))
        if found:
            return found
    return None


def _citation_from_evidence(item: dict) -> Citation:
    return Citation(
        id=str(item.get("id", "unknown")),
        title=str(item.get("source", "知识库资料")),
        url="",
        location="知识库检索",
        snippet=str(item.get("text", ""))[:200],
        score=float(item.get("score", 0.0)),
    )


def _order_answer(order: dict) -> str:
    items = "、".join(f'{item.get("name")}×{item.get("qty")}' for item in order.get("items", []))
    parts = [
        f'订单 {order["order_id"]} 当前状态：{order.get("status_text", order.get("status", "未知"))}。',
        f"下单时间：{order.get('created_at', '未知')}。",
        f"商品：{items or '未知'}，金额：{order.get('amount', '未知')} 元。",
    ]
    if order.get("tracking_no"):
        parts.append(f'承运商：{order.get("carrier")}，运单号：{order["tracking_no"]}。')
    return "".join(parts)


def _logistics_answer(record: dict) -> str:
    nodes = record.get("nodes", [])
    latest = nodes[-1] if nodes else {}
    parts = [
        f'订单 {record["order_id"]} 物流状态：{record.get("current_status", "未知")}。',
        f'承运商：{record.get("carrier")}，运单号：{record.get("tracking_no")}。',
    ]
    if latest:
        parts.append(f'最新轨迹（{latest.get("time", "")}）：{latest.get("text", "")}。')
    return "".join(parts)


def _run_tool(name: str, payload: dict, context: ToolContext, remaining: float):
    # 工具超时不能超过剩余总预算，避免总耗时失控。
    from .tools import get_tool_spec

    spec = get_tool_spec(name)
    limit = spec.timeout_seconds if spec is not None else 3.0
    if remaining < limit:
        limit = max(0.5, remaining)

    result = execute_tool(
        name,
        payload,
        context,
        max_retries=1,
        timeout_seconds=limit,
    )
    return result, result.duration_ms


def run_tool_workflow(
    question: str,
    *,
    pipeline: Any,
    tenant_id: str = "default",
    session_id: str | None = None,
    history: list[dict] | None = None,
    exclude_sources: set[str] | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    total_timeout_seconds: float = DEFAULT_TOTAL_TIMEOUT_SECONDS,
) -> WorkflowOutcome:
    """执行一次最小工具工作流，并写入执行轨迹。"""
    started = time.perf_counter()
    deadline = started + total_timeout_seconds
    trace_id = new_trace_id()
    context = ToolContext(
        tenant_id=tenant_id,
        session_id=session_id,
        pipeline=pipeline,
        exclude_sources=exclude_sources,
    )

    steps: list[dict] = []
    citations: list[Citation] = []
    tool_calls = 0
    usage: dict[str, int] | None = None
    cost: float | None = None
    model = "workflow"
    handoff_reason: str | None = None
    answer = ""
    status: Literal["done", "insufficient"] = "done"
    skip_faq = False
    intent = classify_intent(question)

    def record(action: str, **extra) -> None:
        steps.append({"step": len(steps) + 1, "action": action, **extra})

    def handoff(reason: str, prefix: str) -> str:
        nonlocal handoff_reason, status
        result, duration_ms = _run_tool(
            "human_handoff",
            {"question": question, "reason": reason},
            context,
            deadline - time.perf_counter(),
        )
        record(
            "tool",
            tool="human_handoff",
            status="ok" if result.ok else result.code,
            code=result.code,
            attempts=result.attempts,
            duration_ms=duration_ms,
            input_summary=reason,
        )
        handoff_reason = reason
        if result.ok:
            ticket_id = result.data.get("ticket_id")
            return f"{prefix}（工单号：{ticket_id}）"

        status = "insufficient"
        return f"{prefix}（工单创建失败，请直接联系人工客服）"

    record("intent", intent=intent.intent)

    # 0. 输入护栏：高风险请求不进入检索与生成，直接转人工并记录原因。
    if any(pattern in question.lower() for pattern in INJECTION_PATTERNS):
        answer = handoff("unsafe_request", "这个请求涉及敏感操作，已为您转交人工客服处理。")
        record("guard", triggered=True)

    # 1. 规则意图：投诉 / 明确转人工，直接建单
    if not answer and intent.intent in {"complaint", "human"}:
        reason = "complaint" if intent.intent == "complaint" else "user_request"
        answer = handoff(reason, intent.message or "已为您转接人工客服，请稍候。")
        model = "workflow"

    # 2. 订单 / 物流：问题里带订单号时优先走结构化工具，
    #    否则会被 FAQ 里"订单"这类宽泛关键词截走，拿不到实时状态。
    if not answer:
        order_id = extract_order_id(question)
        from_history = False
        if not order_id:
            order_id = reuse_order_id_from_history(question, history)
            from_history = order_id is not None
        wants_logistics = any(keyword in question for keyword in LOGISTICS_KEYWORDS)
        wants_order = any(keyword in question for keyword in ORDER_KEYWORDS)

        # 只要问题里出现订单号，默认就是问这张订单的状态：不再依赖关键词，
        # 否则「SOxxx 还没付款吗」这类问法会掉到知识检索。
        if order_id and tool_calls < max_steps:
            tool_name = "logistics_track" if wants_logistics else "order_lookup"
            if from_history:
                record("resolve", order_id=order_id, source="history")
            result, duration_ms = _run_tool(
                tool_name, {"order_id": order_id}, context, deadline - time.perf_counter()
            )
            tool_calls += 1
            record(
                "tool",
                tool=tool_name,
                status="ok" if result.ok else result.code,
                code=result.code,
                attempts=result.attempts,
                duration_ms=duration_ms,
                input_summary=order_id,
                reused_from_history=from_history,
            )
            if result.ok:
                payload = result.data["order"] if tool_name == "order_lookup" else result.data["logistics"]
                answer = _order_answer(payload) if tool_name == "order_lookup" else _logistics_answer(payload)
                citations = [
                    Citation(
                        id=f"{tool_name}-{order_id}",
                        title=f"{tool_name}（本地模拟订单系统）",
                        url="",
                        location="结构化工具",
                        snippet=answer[:200],
                        score=1.0,
                    )
                ]
                model = tool_name
            else:
                # 订单查不到时不要让宽泛的 FAQ 关键词给出误导性回答，
                # 直接降级到知识检索，仍无结果则转人工。
                skip_faq = True
                record("fallback", reason=result.code)

    # 3. FAQ 优先命中：零模型成本直接回答
    if not answer and not skip_faq:
        faq_match = find_faq_answer(question, tenant_id=tenant_id)
        if faq_match is not None:
            record("faq", matched=faq_match.get("id", "faq"))
            answer = faq_match["answer"]
            citations = [Citation(**item) for item in faq_match.get("citations", [])]
            model = "faq"

    # 4. 知识检索：走 knowledge_search 工具，再基于证据生成
    if not answer and tool_calls < max_steps:
        result, duration_ms = _run_tool(
            "knowledge_search",
            {"query": question, "top_k": 5},
            context,
            deadline - time.perf_counter(),
        )
        tool_calls += 1
        evidence = (result.data or {}).get("evidence", []) if result.ok else []
        record(
            "tool",
            tool="knowledge_search",
            status="ok" if result.ok else result.code,
            code=result.code,
            attempts=result.attempts,
            duration_ms=duration_ms,
            input_summary=f"top_k=5, hits={len(evidence)}",
        )

        # 相关性阈值：低于阈值视为没有可靠资料，交给转人工兜底。
        threshold = float(os.getenv("RAG_MIN_SCORE", "0") or 0)
        if threshold > 0 and evidence:
            kept = [
                item
                for item in evidence
                if float(item.get("raw_dense_score", 0.0)) >= threshold
            ]
            if len(kept) != len(evidence):
                record(
                    "threshold",
                    kept=len(kept),
                    dropped=len(evidence) - len(kept),
                    threshold=threshold,
                )
            evidence = kept

        if evidence:
            contexts = [
                RetrievedChunk(
                    text=item["text"],
                    metadata={"id": item["id"], "source": item["source"]},
                    combined_score=float(item.get("score", 0.0)),
                    raw_dense_score=float(item.get("raw_dense_score", 0.0)),
                )
                for item in evidence
            ]
            generated = pipeline.generator.generate(question, contexts, history=history)
            answer = generated.text
            citations = [_citation_from_evidence(item) for item in evidence]
            usage = {
                "prompt_tokens": generated.prompt_tokens,
                "completion_tokens": generated.completion_tokens,
                "total_tokens": generated.total_tokens,
            }
            cost = calculate_cost(
                usage,
                input_price_per_million=float(os.getenv("DEEPSEEK_INPUT_PRICE_PER_MILLION", "0")),
                output_price_per_million=float(os.getenv("DEEPSEEK_OUTPUT_PRICE_PER_MILLION", "0")),
            )
            model = "knowledge_search+deepseek"

    # 5. 仍未得到答案：转人工
    if not answer:
        answer = handoff("insufficient_context", "当前资料不足，暂时无法确认答案，已为您转交人工客服跟进。")

    latency_ms = int((time.perf_counter() - started) * 1000)
    if not answer.strip():
        status = "insufficient"

    write_trace(
        {
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "question": question,
            "intent": intent.intent,
            "mode": "tools",
            "model": model,
            "steps": steps,
            "tool_calls": tool_calls,
            "citation_count": len(citations),
            "usage": usage,
            "cost": cost,
            "latency_ms": latency_ms,
            "status": status,
            "handoff_reason": handoff_reason,
        }
    )

    return WorkflowOutcome(
        answer=answer,
        citations=citations,
        status=status,
        trace_id=trace_id,
        steps=steps,
        usage=usage,
        cost=cost,
        latency_ms=latency_ms,
        model=model,
        tool_calls=tool_calls,
        handoff_reason=handoff_reason,
    )
