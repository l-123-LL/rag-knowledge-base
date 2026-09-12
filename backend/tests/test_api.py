import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import PipelineAnswer
from app.retrieval import RetrievedChunk

client = TestClient(app)


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
    ) -> PipelineAnswer:
        if "流感" not in question:
            return PipelineAnswer(answer="当前资料不足。", contexts=[])

        context = RetrievedChunk(
            text="重症流感患者应尽早给予抗流感病毒治疗。",
            metadata={"source": "流感指南", "url": "https://example.com/flu"},
            combined_score=1.0,
        )
        return PipelineAnswer(
            answer="应尽早给予抗流感病毒治疗。",
            contexts=[context],
        )


class FakeStreamingGenerator:
    def stream(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ):
        yield "应尽早"
        yield "给予抗流感病毒治疗。"


class FakeStreamingPipeline:
    def __init__(self) -> None:
        self.generator = FakeStreamingGenerator()

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        exclude_sources: set[str] | None = None,
        tenant_id: str = "default",
    ) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                text="重症流感患者应尽早给予抗流感病毒治疗。",
                metadata={"source": "流感指南"},
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
        json={"text": "示例医学资料。", "source": "示例资料"},
    )
    response = client.post(
        "/ask",
        json={"question": "成人流感的抗病毒治疗时机是什么？"},
    )

    assert ingest_response.status_code == 200
    assert ingest_response.json()["chunk_count"] == 1
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert "抗流感病毒治疗" in payload["answer"]
    assert len(payload["citations"]) == 1


def test_ask_returns_insufficient_for_unknown_question() -> None:
    app.state.pipeline = FakePipeline()
    response = client.post("/ask", json={"question": "今天天气如何"})

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient"
    assert response.json()["citations"] == []


def test_sources_returns_sample_list() -> None:
    response = client.get("/sources")

    assert response.status_code == 200
    assert len(response.json()) >= 5


def test_ingest_file_accepts_text_file() -> None:
    app.state.pipeline = FakePipeline()

    response = client.post(
        "/ingest/file",
        files={"file": ("note.txt", io.BytesIO("流感患者应尽早治疗。".encode()), "text/plain")},
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
        json={"url": "https://example.com/medical"},
    )

    assert response.status_code == 200
    assert response.json()["chunk_count"] == 1


def test_ask_stream_returns_sse() -> None:
    app.state.pipeline = FakeStreamingPipeline()

    response = client.post(
        "/ask/stream",
        json={"question": "流感如何治疗？"},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "应尽早给予抗流感病毒治疗" in response.text


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

    denied = client.post(
        "/faqs",
        json={"question": "问题", "answer": "答案"},
    )
    allowed = client.post(
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
