from pathlib import Path

import pytest

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


def test_load_pdf_raises_for_now() -> None:
    file_path = Path("test_ingestion_tmp.pdf")
    file_path.write_bytes(b"%PDF-1.4")

    try:
        with pytest.raises(NotImplementedError):
            load_text_file(file_path)
    finally:
        file_path.unlink(missing_ok=True)
