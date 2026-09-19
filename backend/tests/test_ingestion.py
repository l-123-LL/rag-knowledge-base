from pathlib import Path

from app.ingestion import clean_html, load_bytes, load_text_file, tables_to_markdown


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


def _pdf_with_text_layer(content: str) -> bytes:
    """构造一个真的带文字层的 PDF（空白页测不出提取链路有没有问题）。"""
    from pypdf import PdfWriter
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 150 Td ({content}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)

    from io import BytesIO

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_load_pdf_extracts_text_layer() -> None:
    # 文本层 PDF 是官方支持路径，必须真的能读出文字（扫描版走 OCR 钩子，不在这一条）
    content = "Refund within 7 days after delivery."

    text, metadata = load_bytes("policy.pdf", _pdf_with_text_layer(content))

    assert content in text
    assert metadata["file_type"] == ".pdf"


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
