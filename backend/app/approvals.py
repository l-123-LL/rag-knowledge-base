"""副作用操作的人工审批：先建审批单，批准后才执行，且同一审批只执行一次。

设计取舍：
- 低风险写操作（本地建工单）直接执行，不拦；
- 高风险写操作（退款、改 CRM 等）必须走审批，且默认只做 dry-run 预演；
- 审批单落盘到 data/approvals/{tenant}/，按租户隔离；
- 幂等：审批单带 idempotency_key，重复批准不会重复执行。
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _approval_dir(tenant_id: str = "default") -> Path:
    safe_tenant = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id)
    return Path(os.getenv("APPROVAL_DIR", "data/approvals")) / safe_tenant


def build_idempotency_key(tool: str, payload: dict, tenant_id: str) -> str:
    """同一租户、同一工具、同一参数的请求视为同一次操作。"""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"{tenant_id}:{tool}:{canonical}"


def find_by_idempotency_key(key: str, tenant_id: str = "default") -> dict | None:
    directory = _approval_dir(tenant_id)
    if not directory.exists():
        return None
    for path in directory.glob("AP*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("idempotency_key") == key:
            return record
    return None


def create_approval(
    tool: str,
    payload: dict,
    tenant_id: str = "default",
    session_id: str | None = None,
    preview: dict | None = None,
) -> dict:
    """创建（或复用）审批单。已存在同幂等键的审批时直接返回它，避免重复建单。"""
    key = build_idempotency_key(tool, payload, tenant_id)
    existing = find_by_idempotency_key(key, tenant_id)
    if existing is not None:
        return existing

    approval_id = f"AP{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    record = {
        "id": approval_id,
        "tool": tool,
        "payload": payload,
        "preview": preview or {},
        "tenant_id": tenant_id,
        "session_id": session_id,
        "status": "pending",
        "idempotency_key": key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decided_at": None,
        "decided_by": None,
        "execution": None,
    }
    directory = _approval_dir(tenant_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{approval_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record


def get_approval(approval_id: str, tenant_id: str = "default") -> dict | None:
    path = _approval_dir(tenant_id) / f"{approval_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_approvals(tenant_id: str = "default", limit: int = 100) -> list[dict]:
    directory = _approval_dir(tenant_id)
    if not directory.exists():
        return []

    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in directory.glob("AP*.json")
    ]
    records.sort(key=lambda item: item["created_at"], reverse=True)
    return records[:limit]


def save_approval(record: dict) -> None:
    directory = _approval_dir(record.get("tenant_id", "default"))
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{record['id']}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def count_pending(tenant_id: str = "default") -> int:
    return sum(1 for item in list_approvals(tenant_id, limit=1000) if item["status"] == "pending")
