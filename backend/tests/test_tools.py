import time
from pathlib import Path

import pytest

from app.retrieval import RetrievedChunk
from app.tools import (
    TOOL_REGISTRY,
    KnowledgeSearchInput,
    ToolContext,
    ToolErrorCode,
    ToolResult,
    ToolSpec,
    execute_tool,
    list_tool_names,
)


class FakePipeline:
    def retrieve(self, question, top_k=5, exclude_sources=None, tenant_id="default"):
        return [
            RetrievedChunk(
                text="签收后 7 天内可申请无理由退货。",
                metadata={"id": "chunk-1", "source": "售后政策"},
                combined_score=0.92,
                raw_dense_score=0.71,
            )
        ]


@pytest.fixture(autouse=True)
def isolated_ticket_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # 工具会产生真实副作用（建工单），测试统一写到临时目录。
    monkeypatch.setenv("TICKET_DIR", str(tmp_path / "tickets"))


def test_registry_contains_four_tools() -> None:
    assert list_tool_names() == [
        "human_handoff",
        "knowledge_search",
        "logistics_track",
        "order_lookup",
    ]


def test_knowledge_search_returns_evidence() -> None:
    result = execute_tool(
        "knowledge_search",
        {"query": "退货政策", "top_k": 3},
        ToolContext(pipeline=FakePipeline()),
    )

    assert result.ok
    assert result.data["count"] == 1
    assert result.data["evidence"][0]["source"] == "售后政策"
    assert result.data["evidence"][0]["raw_dense_score"] == 0.71


def test_order_lookup_masks_phone() -> None:
    result = execute_tool("order_lookup", {"order_id": "SO20260901001"}, ToolContext())

    assert result.ok
    order = result.data["order"]
    assert order["status_text"] == "已发货"
    assert order["receiver_phone"] == "138****8001"


def test_order_lookup_respects_tenant_isolation() -> None:
    # SO20260901019 属于 acme 租户，默认租户查不到。
    result = execute_tool("order_lookup", {"order_id": "SO20260901019"}, ToolContext())

    assert not result.ok
    assert result.code == ToolErrorCode.NOT_FOUND
    assert result.attempts == 1  # 查不到属于非重试类错误


def test_logistics_track_returns_latest_node() -> None:
    result = execute_tool("logistics_track", {"order_id": "SO20260901006"}, ToolContext())

    assert result.ok
    assert result.data["logistics"]["current_status"] == "派送中"


def test_invalid_argument_is_rejected() -> None:
    result = execute_tool("order_lookup", {"order_id": "x"}, ToolContext())

    assert not result.ok
    assert result.code == ToolErrorCode.INVALID_ARGUMENT


def test_unknown_tool_is_rejected() -> None:
    result = execute_tool("not_a_tool", {}, ToolContext())

    assert not result.ok
    assert result.code == ToolErrorCode.INVALID_ARGUMENT


def test_human_handoff_creates_local_ticket() -> None:
    result = execute_tool(
        "human_handoff",
        {"question": "我要投诉", "reason": "complaint"},
        ToolContext(session_id="s-1"),
    )

    assert result.ok
    assert result.data["ticket_id"].startswith("T")
    assert result.data["reason"] == "complaint"


def test_timeout_is_retried_then_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def slow_handler(payload, context):
        calls["count"] += 1
        time.sleep(0.2)
        return ToolResult(ok=True)

    monkeypatch.setitem(
        TOOL_REGISTRY,
        "slow_tool",
        ToolSpec(
            name="slow_tool",
            description="test only",
            input_model=KnowledgeSearchInput,
            handler=slow_handler,
            timeout_seconds=0.05,
            max_retries=1,
        ),
    )

    result = execute_tool("slow_tool", {"query": "x"}, ToolContext())

    assert result.code == ToolErrorCode.UPSTREAM_TIMEOUT
    assert result.retryable
    assert result.attempts == 2
    assert calls["count"] == 2


def test_retryable_failure_can_recover_on_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"count": 0}

    def flaky_handler(payload, context):
        state["count"] += 1
        if state["count"] == 1:
            return ToolResult(
                ok=False,
                code=ToolErrorCode.INTERNAL,
                error="第一次失败",
                retryable=True,
            )
        return ToolResult(ok=True, data={"recovered": True})

    monkeypatch.setitem(
        TOOL_REGISTRY,
        "flaky_tool",
        ToolSpec(
            name="flaky_tool",
            description="test only",
            input_model=KnowledgeSearchInput,
            handler=flaky_handler,
            timeout_seconds=1.0,
            max_retries=1,
        ),
    )

    result = execute_tool("flaky_tool", {"query": "x"}, ToolContext())

    assert result.ok
    assert result.attempts == 2
    assert result.data == {"recovered": True}
