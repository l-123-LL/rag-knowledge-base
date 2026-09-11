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

    def answer(self, question: str, top_k: int = 5) -> PipelineAnswer:
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
