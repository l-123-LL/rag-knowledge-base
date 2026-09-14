import json
import os
import re
from pathlib import Path


def _session_path(session_id: str, tenant_id: str = "default") -> Path:
    base = Path(os.getenv("SESSION_DIR", "data/sessions"))
    safe_tenant = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
    return base / safe_tenant / f"{safe_id}.json"


def get_history(
    session_id: str | None,
    max_messages: int = 8,
    tenant_id: str = "default",
) -> list[dict]:
    """只取最近 N 条消息，避免上下文无限膨胀。"""
    if not session_id:
        return []

    path = _session_path(session_id, tenant_id)
    if not path.exists():
        return []

    messages = json.loads(path.read_text(encoding="utf-8"))
    return messages[-max_messages:]


def record_message(
    session_id: str | None,
    role: str,
    content: str,
    tenant_id: str = "default",
) -> None:
    # 先读后写，保持单会话 JSON 结构简单、可恢复。
    if not session_id:
        return

    path = _session_path(session_id, tenant_id)
    messages = []
    if path.exists():
        messages = json.loads(path.read_text(encoding="utf-8"))
    messages.append({"role": role, "content": content})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")


def clear_session(session_id: str, tenant_id: str = "default") -> None:
    _session_path(session_id, tenant_id).unlink(missing_ok=True)


def count_sessions(tenant_id: str = "default") -> int:
    base = Path(os.getenv("SESSION_DIR", "data/sessions"))
    safe_tenant = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id)
    tenant_dir = base / safe_tenant
    return len(list(tenant_dir.glob("*.json"))) if tenant_dir.exists() else 0
