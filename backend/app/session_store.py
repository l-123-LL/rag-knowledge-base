import json
import os
import re
from pathlib import Path


def _session_path(session_id: str) -> Path:
    base = Path(os.getenv("SESSION_DIR", "data/sessions"))
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
    return base / f"{safe_id}.json"


def get_history(session_id: str | None, max_messages: int = 8) -> list[dict]:
    if not session_id:
        return []

    path = _session_path(session_id)
    if not path.exists():
        return []

    messages = json.loads(path.read_text(encoding="utf-8"))
    return messages[-max_messages:]


def record_message(session_id: str | None, role: str, content: str) -> None:
    if not session_id:
        return

    path = _session_path(session_id)
    messages = []
    if path.exists():
        messages = json.loads(path.read_text(encoding="utf-8"))
    messages.append({"role": role, "content": content})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")


def clear_session(session_id: str) -> None:
    _session_path(session_id).unlink(missing_ok=True)


def count_sessions() -> int:
    base = Path(os.getenv("SESSION_DIR", "data/sessions"))
    return len(list(base.glob("*.json"))) if base.exists() else 0
