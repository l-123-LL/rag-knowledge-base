from pathlib import Path

from app.faq_store import add_faq, delete_faq, list_faqs, update_faq


def test_faq_store_crud(monkeypatch) -> None:
    directory = Path("test_faq_data")
    monkeypatch.setenv("FAQ_DIR", str(directory))
    try:
        item = add_faq(
            question="如何修改地址？",
            answer="发货前可在订单详情修改。",
            keywords=["修改地址"],
            tenant_id="tenant-a",
        )
        updated = update_faq(
            faq_id=item["id"],
            question="如何修改收货地址？",
            answer="发货前可在订单详情修改地址。",
            keywords=["修改地址", "收货地址"],
            tenant_id="tenant-a",
        )
        removed = delete_faq(item["id"], tenant_id="tenant-a")
        items = list_faqs("tenant-a")
    finally:
        path = directory / "tenant-a.json"
        path.unlink(missing_ok=True)
        directory.rmdir()

    assert item["version"] == 1
    assert updated is not None
    assert updated["version"] == 2
    assert removed is True
    assert items == []
