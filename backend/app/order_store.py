"""本地模拟订单与物流数据读取。

数据是本地 mock，不是真实业务系统；查询函数签名与真实 adapter 保持一致，
后续接入真实订单系统时只需要替换本文件的实现。
"""

import json
import os
from functools import lru_cache
from pathlib import Path


def _mock_file() -> Path:
    override = os.getenv("MOCK_DATA_DIR")
    base = Path(override) if override else Path(__file__).resolve().parents[1] / "mock"
    return base / "orders.json"


@lru_cache(maxsize=1)
def _load_payload(path: str, mtime: float) -> dict:
    # mtime 参与缓存键，文件被修改后自动失效，方便本地改数据调试。
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load() -> dict:
    path = _mock_file()
    if not path.exists():
        return {"orders": [], "logistics": []}
    return _load_payload(str(path), path.stat().st_mtime)


def mask_phone(phone: str | None) -> str | None:
    """手机号脱敏，避免把完整号码写进回答和日志。"""
    if not phone or len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def find_order(order_id: str, tenant_id: str = "default") -> dict | None:
    """按订单号查询，并做租户隔离。"""
    target = order_id.strip().upper()
    for order in _load()["orders"]:
        if order["order_id"].upper() == target and order.get("tenant_id", "default") == tenant_id:
            return dict(order)
    return None


def find_logistics(order_id: str, tenant_id: str = "default") -> dict | None:
    """按订单号查询物流轨迹，先做租户校验再返回。"""
    if find_order(order_id, tenant_id=tenant_id) is None:
        return None

    target = order_id.strip().upper()
    for record in _load()["logistics"]:
        if record["order_id"].upper() == target:
            return dict(record)
    return None
