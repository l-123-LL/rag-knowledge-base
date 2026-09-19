from pathlib import Path

import pytest

from app.faq_store import (
    add_faq,
    delete_faq,
    find_faq_answer,
    list_faqs,
    update_faq,
)


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


@pytest.fixture
def faq_dir(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("FAQ_DIR", str(tmp_path))
    return tmp_path


def test_faq_match_uses_keyword(faq_dir: Path) -> None:
    match = find_faq_answer("无理由退货要几天？")

    assert match is not None
    assert match["id"] == "faq-return"


def test_exception_question_skips_faq(faq_dir: Path) -> None:
    # 通用 FAQ 答案是「7 天内可无理由退货」，语料里还有「定制类商品除外」这样的例外。
    # 问定制商品时必须放行给检索，否则会给用户一个盖掉例外的错误承诺。
    assert find_faq_answer("定制商品可以无理由退货吗？") is None
    assert find_faq_answer("生鲜类商品支持退货吗？") is None


def test_exception_markers_can_be_disabled(faq_dir: Path, monkeypatch) -> None:
    # 显式写 none 才关闭这层保护（留空仍然用默认列表），回到纯关键词匹配
    monkeypatch.setenv("FAQ_EXCEPTION_MARKERS", "none")

    match = find_faq_answer("定制商品可以无理由退货吗？")

    assert match is not None
    assert match["id"] == "faq-return"


def test_exception_markers_support_custom_list(faq_dir: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAQ_EXCEPTION_MARKERS", "预售")

    assert find_faq_answer("预售商品可以退货吗？") is None
    # 自定义列表会覆盖默认列表：定制不在列表里，于是回到 FAQ
    assert find_faq_answer("定制商品可以退货吗？") is not None


def test_generic_keyword_does_not_capture_unrelated_question(faq_dir: Path) -> None:
    # 实测问题：发货 FAQ 的关键词里只要有「订单」，任何带「订单」的问题都会被吸走，
    # 「litemall 的商城功能里有没有订单售后？」曾被答成"24 小时内发货"。
    # 关键词必须足够具体，通用词单独命中不算。
    assert find_faq_answer("litemall 的商城功能里有没有订单售后？") is None
    # 真正的发货问题仍然要命中
    assert find_faq_answer("我的订单什么时候发货？") is not None
