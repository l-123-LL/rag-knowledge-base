import json
from pathlib import Path

from app.observability import log_ask_event


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
