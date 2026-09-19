from pathlib import Path

from app.ingestion import clean_html, load_text_file, tables_to_markdown


def test_clean_html_removes_script_and_tags() -> None:
    content = "<html><script>alert(1)</script><p>退款处理</p></html>"

    assert "退款处理" in clean_html(content)
    assert "alert" not in clean_html(content)


def test_load_text_file_reads_utf8() -> None:
    file_path = Path("test_ingestion_tmp.txt")
    file_path.write_text("物流应低盐饮食。", encoding="utf-8")

    try:
        text, metadata = load_text_file(file_path)
    finally:
        file_path.unlink(missing_ok=True)

    assert text == "物流应低盐饮食。"
    assert metadata["file_name"] == "test_ingestion_tmp.txt"


def test_load_pdf_returns_text() -> None:
    file_path = Path("test_ingestion_tmp.pdf")
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with file_path.open("wb") as handle:
        writer.write(handle)

    try:
        text, metadata = load_text_file(file_path)
    finally:
        file_path.unlink(missing_ok=True)

    assert isinstance(text, str)
    assert metadata["file_name"] == "test_ingestion_tmp.pdf"


def test_tables_to_markdown() -> None:
    markdown = tables_to_markdown(
        [
            [
                ["商品", "退货天数"],
                ["普通商品", "7 天"],
            ]
        ]
    )

    assert "| 商品 | 退货天数 |" in markdown
    assert "| 普通商品 | 7 天 |" in markdown
