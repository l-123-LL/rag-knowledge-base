from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ask_returns_answer_for_known_question() -> None:
    response = client.post(
        "/ask",
        json={"question": "成人流感的抗病毒治疗时机是什么？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert "抗流感病毒治疗" in payload["answer"]
    assert len(payload["citations"]) == 1


def test_ask_returns_insufficient_for_unknown_question() -> None:
    response = client.post("/ask", json={"question": "今天天气如何"})

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient"
    assert response.json()["citations"] == []


def test_sources_returns_sample_list() -> None:
    response = client.get("/sources")

    assert response.status_code == 200
    assert len(response.json()) == 5
