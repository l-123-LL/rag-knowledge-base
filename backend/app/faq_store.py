import json
import os
import re
import threading
import uuid
from pathlib import Path

from .schemas import Citation

_lock = threading.RLock()


def _faq_path(tenant_id: str) -> Path:
    """每个租户一个 FAQ 文件，避免不同企业数据互相覆盖。"""
    base = Path(os.getenv("FAQ_DIR", "data/faqs"))
    safe_tenant = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id)
    return base / f"{safe_tenant}.json"


def _default_items() -> list[dict]:
    return [
        {
            "id": "faq-return",
            "question": "如何申请退货？",
            "answer": "收到商品后 7 天内可申请无理由退货，商品需保持完好且不影响二次销售。",
            "keywords": ["退货", "退款", "退换货", "无理由"],
            "tenant_id": "default",
            "version": 1,
            "citations": [
                Citation(
                    id="faq-return-cite",
                    title="退换货政策说明",
                    url="https://example.com/support/returns",
                    location="FAQ",
                    snippet="收到商品后 7 天内可申请无理由退货，商品需保持完好且不影响二次销售。",
                    score=1.0,
                ).model_dump()
            ],
        },
        {
            "id": "faq-shipping",
            "question": "我的订单什么时候发货？",
            "answer": "现货订单通常在工作日 24 小时内发出，发货后可在订单详情查看物流单号。",
            "keywords": ["发货", "物流", "配送", "订单"],
            "tenant_id": "default",
            "version": 1,
            "citations": [
                Citation(
                    id="faq-shipping-cite",
                    title="订单与物流说明",
                    url="https://example.com/support/shipping",
                    location="FAQ",
                    snippet="现货订单通常在工作日 24 小时内发出，发货后可在订单详情查看物流单号。",
                    score=1.0,
                ).model_dump()
            ],
        },
        {
            "id": "faq-invoice",
            "question": "如何申请发票？",
            "answer": "订单完成后可在个人中心申请电子发票，开票信息需与订单抬头一致。",
            "keywords": ["发票", "开票", "电子发票"],
            "tenant_id": "default",
            "version": 1,
            "citations": [
                Citation(
                    id="faq-invoice-cite",
                    title="发票申请说明",
                    url="https://example.com/support/invoice",
                    location="FAQ",
                    snippet="订单完成后可在个人中心申请电子发票，开票信息需与订单抬头一致。",
                    score=1.0,
                ).model_dump()
            ],
        },
        {
            "id": "faq-human",
            "question": "怎么联系人工客服？",
            "answer": "如需人工客服，可在服务页面选择转人工，服务时间为工作日 9:00-18:00。",
            "keywords": ["人工客服", "转人工", "人工", "客服"],
            "tenant_id": "default",
            "version": 1,
            "citations": [
                Citation(
                    id="faq-human-cite",
                    title="人工客服转接说明",
                    url="https://example.com/support/human",
                    location="FAQ",
                    snippet="如需人工客服，可在服务页面选择转人工，服务时间为工作日 9:00-18:00。",
                    score=1.0,
                ).model_dump()
            ],
        },
    ]


def _load(tenant_id: str) -> list[dict]:
    path = _faq_path(tenant_id)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save(tenant_id: str, items: list[dict]) -> None:
    path = _faq_path(tenant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def list_faqs(tenant_id: str = "default") -> list[dict]:
    # 首次访问默认租户时写入内置 FAQ，后续直接读磁盘。
    with _lock:
        items = _load(tenant_id)
        if not items and tenant_id == "default":
            items = _default_items()
            _save(tenant_id, items)
        return items


def find_faq_answer(question: str, tenant_id: str = "default") -> dict | None:
    # FAQ 精确优先，先归一化空格，再按关键词包含匹配。
    normalized = question.lower().replace(" ", "")
    for item in list_faqs(tenant_id):
        if any(
            keyword.lower().replace(" ", "") in normalized
            for keyword in item.get("keywords", [])
        ):
            return item
    return None


def faq_count(tenant_id: str = "default") -> int:
    return len(list_faqs(tenant_id))


def add_faq(
    question: str,
    answer: str,
    keywords: list[str],
    source: str = "人工录入",
    tenant_id: str = "default",
) -> dict:
    # 加锁写文件，防止多线程同时修改造成数据丢失。
    with _lock:
        items = list_faqs(tenant_id)
        item = {
            "id": f"faq-{uuid.uuid4().hex[:8]}",
            "question": question,
            "answer": answer,
            "keywords": keywords or [question],
            "tenant_id": tenant_id,
            "version": 1,
            "citations": [
                Citation(
                    id=f"faq-cite-{uuid.uuid4().hex[:8]}",
                    title=source,
                    url="",
                    location="FAQ",
                    snippet=answer[:200],
                    score=1.0,
                ).model_dump()
            ],
        }
        items.append(item)
        _save(tenant_id, items)
        return item


def update_faq(
    faq_id: str,
    question: str,
    answer: str,
    keywords: list[str],
    tenant_id: str = "default",
) -> dict | None:
    with _lock:
        items = list_faqs(tenant_id)
        for item in items:
            if item["id"] == faq_id:
                item["question"] = question
                item["answer"] = answer
                item["keywords"] = keywords or [question]
                item["version"] = item.get("version", 1) + 1
                if item.get("citations"):
                    item["citations"][0]["snippet"] = answer[:200]
                _save(tenant_id, items)
                return item
    return None


def delete_faq(faq_id: str, tenant_id: str = "default") -> bool:
    with _lock:
        items = list_faqs(tenant_id)
        remaining = [item for item in items if item["id"] != faq_id]
        if len(remaining) == len(items):
            return False
        _save(tenant_id, remaining)
        return True
