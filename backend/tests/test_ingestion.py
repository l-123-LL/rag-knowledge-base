from pathlib import Path

from app.ingestion import clean_html, load_text_file


def test_clean_html_removes_script_and_tags() -> None:
    content = "<html><script>alert(1)</script><p>流感治疗</p></html>"

    assert "流感治疗" in clean_html(content)
    assert "alert" not in clean_html(content)


def test_load_text_file_reads_utf8() -> None:
    file_path = Path("test_ingestion_tmp.txt")
    file_path.write_text("高血压应低盐饮食。", encoding="utf-8")

    try:
        text, metadata = load_text_file(file_path)
    finally:
        file_path.unlink(missing_ok=True)

    assert text == "高血压应低盐饮食。"
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
