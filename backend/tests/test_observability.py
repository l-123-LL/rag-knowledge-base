import json
from pathlib import Path

from app.observability import (
    log_ask_event,
    log_feedback,
    summarize_ask_log,
    summarize_feedback,
)


def test_log_ask_event_writes_jsonl() -> None:
    path = Path("test_ask_log.jsonl")
    try:
        log_ask_event({"question": "如何申请退货？", "model": "faq"}, path)
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)

    assert payload["question"] == "如何申请退货？"
    assert payload["model"] == "faq"
    assert "timestamp" in payload


def test_summarize_ask_log() -> None:
    path = Path("test_metrics_log.jsonl")
    try:
        log_ask_event(
            {
                "route": "faq",
                "latency_ms": 10,
                "usage": {"total_tokens": 0},
                "cost": 0.0,
            },
            path,
        )
        log_ask_event(
            {
                "route": "rag",
                "latency_ms": 20,
                "usage": {"total_tokens": 100},
                "cost": 0.01,
            },
            path,
        )
        summary = summarize_ask_log(path)
    finally:
        path.unlink(missing_ok=True)

    assert summary["total_queries"] == 2
    assert summary["route_counts"]["rag"] == 1
    assert summary["avg_latency_ms"] == 15
    assert summary["total_tokens"] == 100


def test_log_feedback_writes_jsonl() -> None:
    path = Path("test_feedback_log.jsonl")
    try:
        log_feedback({"rating": "up", "question": "如何退货？"}, path)
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)

    assert payload["rating"] == "up"
    assert payload["question"] == "如何退货？"


def test_summarize_feedback() -> None:
    path = Path("test_feedback_summary.jsonl")
    try:
        log_feedback({"rating": "up"}, path)
        log_feedback({"rating": "up"}, path)
        log_feedback({"rating": "down"}, path)
        summary = summarize_feedback(path)
    finally:
        path.unlink(missing_ok=True)

    assert summary["feedback_count"] == 3
    assert summary["up_count"] == 2
    assert summary["down_count"] == 1
    assert round(summary["helpful_rate"], 2) == 0.67
