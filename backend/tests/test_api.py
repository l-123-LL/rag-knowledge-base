import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import PipelineAnswer
from app.retrieval import RetrievedChunk

client = TestClient(app)
client.headers.update({"X-API-Key": "test-admin-key"})


@pytest.fixture(autouse=True)
def configure_admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")


class FakePipeline:
    def ingest_text(self, text: str, metadata: dict | None = None) -> int:
        self.text = text
        return 1

    def answer(
        self,
        question: str,
        top_k: int = 5,
        history: list[dict] | None = None,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> PipelineAnswer:
        if "退款" not in question:
            return PipelineAnswer(answer="当前资料不足。", contexts=[])

        context = RetrievedChunk(
            text="退款需在订单完成后 7 天内提交，商家审核后原路退回。",
            metadata={"source": "售后政策", "url": "https://example.com/refund"},
            combined_score=1.0,
        )
        return PipelineAnswer(
            answer="审核通过后给予原路退回。",
            contexts=[context],
        )


class FakeStreamingGenerator:
    def stream(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ):
        yield "审核通过后"
        yield "给予原路退回。"


class FakeStreamingPipeline:
    def __init__(self) -> None:
        self.generator = FakeStreamingGenerator()

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
        as_of: str | None = None,
    ) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                text="退款需在订单完成后 7 天内提交，商家审核后原路退回。",
                metadata={"source": "售后政策"},
                combined_score=1.0,
            )
        ]


@pytest.fixture(autouse=True)
def reset_pipeline() -> None:
    app.state.pipeline = None
    yield
    app.state.pipeline = None


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_then_ask_returns_answer() -> None:
    app.state.pipeline = FakePipeline()

    ingest_response = client.post(
        "/ingest",
        json={"text": "示例售后资料。", "source": "示例资料"},
    )
    response = client.post(
        "/ask",
        json={"question": "退款多久到账？"},
    )

    assert ingest_response.status_code == 200
    assert ingest_response.json()["chunk_count"] == 1
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    # 这个问题会被 FAQ 关键词命中，因此返回标准答案（含 7 天政策与引用）
    assert "7 天" in payload["answer"]
    assert len(payload["citations"]) == 1


def test_ask_returns_insufficient_for_unknown_question() -> None:
    app.state.pipeline = FakePipeline()
    response = client.post("/ask", json={"question": "今天天气如何"})

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient"
    assert response.json()["citations"] == []


def test_insufficient_answer_escalates_to_human() -> None:
    # 检索不到资料时不能只回一句“不知道”，要给出转人工出口和工单号。
    app.state.pipeline = FakePipeline()

    response = client.post("/ask", json={"question": "今天天气如何"})

    payload = response.json()
    assert payload["status"] == "insufficient"
    assert "转交人工客服" in payload["answer"]
    assert "工单号" in payload["answer"]


def test_insufficient_answer_creates_ticket_with_reason() -> None:
    app.state.pipeline = FakePipeline()

    response = client.post("/ask", json={"question": "今天天气如何"})
    ticket_id = response.json()["answer"].split("工单号：")[1].rstrip("）")
    tickets = client.get("/tickets").json()

    ticket = next(item for item in tickets if item["id"] == ticket_id)
    assert ticket["reason"] == "insufficient_context"


def test_informational_agent_question_is_answered_by_faq() -> None:
    app.state.pipeline = None

    response = client.post("/ask", json={"question": "怎么联系人工客服？"})

    payload = response.json()
    assert payload["model"] == "faq"
    assert "9:00-18:00" in payload["answer"]


def test_asked_not_to_transfer_is_not_transferred() -> None:
    app.state.pipeline = None

    response = client.post(
        "/ask",
        json={"question": "我不想转人工，你们几点发货？"},
    )

    assert response.json()["model"] != "intent"


def test_sources_returns_sample_list() -> None:
    response = client.get("/sources")

    assert response.status_code == 200
    assert len(response.json()) >= 5


def test_ingest_file_accepts_text_file() -> None:
    app.state.pipeline = FakePipeline()

    response = client.post(
        "/ingest/file",
        files={"file": ("note.txt", io.BytesIO("退款需商家审核。".encode()), "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["chunk_count"] == 1


def test_ingest_url_accepts_public_page(monkeypatch: pytest.MonkeyPatch) -> None:
    app.state.pipeline = FakePipeline()
    monkeypatch.setattr(
        "app.main.fetch_url_text",
        lambda url: ("网页正文内容", {"file_name": url}),
    )

    response = client.post(
        "/ingest/url",
        json={"url": "https://example.com/policy"},
    )

    assert response.status_code == 200
    assert response.json()["chunk_count"] == 1


def test_ask_stream_returns_sse() -> None:
    app.state.pipeline = FakeStreamingPipeline()

    response = client.post(
        "/ask/stream",
        json={"question": "退款怎么处理？"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "7 天" in response.text


def test_faq_question_returns_standard_answer_without_pipeline() -> None:
    app.state.pipeline = None

    response = client.post(
        "/ask",
        json={"question": "如何申请退货？"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "faq"
    assert response.json()["status"] == "done"


def test_complaint_intent_returns_transfer_message() -> None:
    app.state.pipeline = None

    response = client.post(
        "/ask",
        json={"question": "我要投诉你们的客服"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "intent"
    assert "投诉" in response.json()["answer"]


def test_human_intent_returns_transfer_message() -> None:
    app.state.pipeline = None

    response = client.post(
        "/ask",
        json={"question": "请帮我转人工客服"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "intent"
    assert "转接人工" in response.json()["answer"]


def test_session_reset_clears_history() -> None:
    response = client.post(
        "/session/reset",
        json={"session_id": "test-session"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_stats_returns_counts() -> None:
    response = client.get("/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_count"] >= 5
    assert payload["faq_count"] >= 4
    assert payload["ticket_count"] >= 0


def test_create_faq_is_used_by_ask() -> None:
    created = client.post(
        "/faqs",
        json={
            "question": "如何修改收货地址？",
            "answer": "订单发货前可在订单详情中修改收货地址。",
            "keywords": ["修改地址", "收货地址"],
            "source": "客服手册",
        },
    )

    assert created.status_code == 200
    response = client.post(
        "/ask",
        json={"question": "我想修改地址"},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "faq"
    assert "发货前" in response.json()["answer"]


def test_update_and_delete_faq() -> None:
    created = client.post(
        "/faqs",
        json={
            "question": "如何修改手机号？",
            "answer": "在账号设置中修改。",
            "keywords": ["修改手机号"],
        },
    ).json()
    updated = client.put(
        f"/faqs/{created['id']}",
        json={
            "question": "怎么修改手机号？",
            "answer": "在账号安全设置中修改手机号。",
            "keywords": ["修改手机号", "手机号"],
        },
    )
    deleted = client.delete(f"/faqs/{created['id']}")

    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert deleted.status_code == 200


def test_archive_and_restore_source() -> None:
    archived = client.post(
        "/sources/return-policy/archive",
        params={"archived": True},
    )
    restored = client.post(
        "/sources/return-policy/archive",
        params={"archived": False},
    )

    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert restored.status_code == 200
    assert restored.json()["archived"] is False


def test_feedback_endpoint() -> None:
    response = client.post(
        "/feedback",
        json={
            "question": "如何申请退货？",
            "rating": "up",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_key_is_enforced_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "secret-key")
    plain_client = TestClient(app)

    denied = plain_client.post(
        "/faqs",
        json={"question": "问题", "answer": "答案"},
    )
    allowed = plain_client.post(
        "/faqs",
        headers={"X-API-Key": "secret-key"},
        json={"question": "问题2", "answer": "答案2"},
    )

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    main._request_times.clear()

    first = client.get("/sources")
    second = client.get("/sources")

    assert first.status_code == 200
    assert second.status_code == 429


def test_intent_creates_ticket() -> None:
    app.state.pipeline = None

    response = client.post(
        "/ask",
        json={"question": "我要投诉", "session_id": "ticket-test"},
    )

    assert response.status_code == 200
    assert "工单号" in response.json()["answer"]


def test_tickets_endpoint_returns_created_ticket() -> None:
    created = client.post(
        "/tickets",
        json={"question": "需要人工处理", "reason": "manual"},
    )
    tickets = client.get("/tickets")

    assert created.status_code == 200
    assert created.json()["id"].startswith("T")
    assert any(item["id"] == created.json()["id"] for item in tickets.json())


def test_oidc_requires_bearer_token_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OIDC_JWKS_URL", "https://example.com/jwks")

    response = client.post("/ask", json={"question": "如何申请退货？"})

    assert response.status_code == 401


def test_alerts_endpoint_returns_status() -> None:
    response = client.get("/alerts")

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "warning"}


def test_persisted_chunk_count_reads_records(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    directory = Path("test_faiss_stats")
    directory.mkdir(exist_ok=True)
    records = directory / "records.json"
    records.write_text(
        json.dumps({"1": {}, "2": {}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("FAISS_DIR", str(directory))

    try:
        assert main.persisted_chunk_count() == 2
    finally:
        records.unlink(missing_ok=True)
        directory.rmdir()


class FakeToolPipeline:
    """tools 模式下的假管线：只提供工作流需要的 retrieve 与 generator。"""

    class _Generator:
        def generate(self, question, contexts, history=None):
            from app.generation import GenerationResult

            return GenerationResult(
                text="根据资料：签收后 7 天内可申请无理由退货。",
                prompt_tokens=20,
                completion_tokens=8,
                total_tokens=28,
            )

    def __init__(self) -> None:
        self.generator = self._Generator()

    def retrieve(self, question, top_k=5, exclude_sources=None, tenant_id="default"):
        return [
            RetrievedChunk(
                text="签收后 7 天内可申请无理由退货。",
                metadata={"id": "chunk-1", "source": "售后政策"},
                combined_score=0.9,
                raw_dense_score=0.72,
            )
        ]


def test_tools_mode_returns_trace_and_order_answer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TICKET_DIR", str(tmp_path / "tickets"))
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))
    app.state.pipeline = FakeToolPipeline()

    response = client.post(
        "/ask",
        json={"question": "订单 SO20260901001 现在什么状态", "workflow_mode": "tools"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["model"] == "order_lookup"
    assert payload["trace_id"].startswith("tr_")
    assert payload["steps"][0]["action"] == "intent"

    trace = client.get(f"/traces/{payload['trace_id']}")
    assert trace.status_code == 200
    assert trace.json()["trace_id"] == payload["trace_id"]
    assert trace.json()["tool_calls"] == 1


def test_tools_mode_available_on_stream_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("TICKET_DIR", str(tmp_path / "tickets"))
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))
    app.state.pipeline = FakeToolPipeline()

    response = client.post(
        "/ask/stream",
        json={"question": "订单 SO20260901001 现在什么状态", "workflow_mode": "tools"},
    )

    assert response.status_code == 200
    assert "已发货" in response.text


def test_default_workflow_mode_keeps_rag_behaviour(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # 不传 workflow_mode 时必须与升级前一致：FAQ 分支、无 trace_id。
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))
    app.state.pipeline = None

    response = client.post("/ask", json={"question": "如何申请退货？"})

    payload = response.json()
    assert payload["model"] == "faq"
    assert payload["trace_id"] is None
    assert payload["steps"] is None


def test_trace_endpoint_returns_404_for_unknown_id() -> None:
    response = client.get("/traces/tr_not_exists")

    assert response.status_code == 404


def test_refund_approval_flow_via_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("APPROVAL_DIR", str(tmp_path / "approvals"))
    monkeypatch.setenv("TICKET_DIR", str(tmp_path / "tickets"))
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))
    app.state.pipeline = FakeToolPipeline()

    asked = client.post(
        "/ask",
        json={"question": "订单 SO20260901001 我要退款", "workflow_mode": "tools"},
    ).json()
    assert "审批号" in asked["answer"]

    approvals = client.get("/approvals").json()
    assert approvals and approvals[0]["status"] == "pending"

    approved = client.post(
        f"/approvals/{approvals[0]['id']}/decision",
        json={"approved": True},
    ).json()
    assert approved["status"] == "executed"
    assert approved["execution"]["data"]["ticket_id"].startswith("T")

    # 幂等：重复批准不会重复执行
    again = client.post(
        f"/approvals/{approvals[0]['id']}/decision",
        json={"approved": True},
    ).json()
    assert again["status"] == "executed"
    assert again["execution"] == approved["execution"]
