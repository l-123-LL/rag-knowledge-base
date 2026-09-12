import json
import os
from datetime import datetime, timezone
from pathlib import Path


def log_ask_event(event: dict, log_path: str | Path | None = None) -> None:
    """把问答事件追加到 JSONL 日志，后续可替换为 Langfuse。"""
    path = Path(log_path or os.getenv("ASK_LOG_PATH", "data/logs/ask.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
