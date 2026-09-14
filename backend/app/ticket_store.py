import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


def _ticket_dir(tenant_id: str = "default") -> Path:
    return Path(os.getenv("TICKET_DIR", "data/tickets")) / tenant_id


def create_ticket(
    question: str,
    session_id: str | None = None,
    reason: str = "customer_service",
    tenant_id: str = "default",
) -> dict:
    """创建本地工单并持久化，配置 Webhook 时同步外发。"""
    ticket_id = f"T{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    ticket = {
        "id": ticket_id,
        "question": question,
        "session_id": session_id,
        "reason": reason,
        "status": "open",
        "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    directory = _ticket_dir(tenant_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{ticket_id}.json").write_text(
        json.dumps(ticket, ensure_ascii=False),
        encoding="utf-8",
    )
    send_ticket_webhook(ticket)
    return ticket


def list_tickets(limit: int = 100, tenant_id: str = "default") -> list[dict]:
    directory = _ticket_dir(tenant_id)
    if not directory.exists():
        return []

    tickets = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in directory.glob("T*.json")
    ]
    tickets.sort(key=lambda item: item["created_at"], reverse=True)
    return tickets[:limit]


def count_tickets(tenant_id: str = "default") -> int:
    directory = _ticket_dir(tenant_id)
    return len(list(directory.glob("T*.json"))) if directory.exists() else 0


def send_ticket_webhook(ticket: dict) -> bool:
    # 外发失败不影响工单保存，保证客服主流程可用。
    """可选工单外发：配置 TICKET_WEBHOOK_URL 后推送到 CRM 或客服平台。"""
    url = os.getenv("TICKET_WEBHOOK_URL")
    if not url:
        return False

    try:
        response = httpx.post(url, json=ticket, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        return False

    return True
