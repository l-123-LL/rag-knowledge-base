import html
import re
from pathlib import Path


def clean_html(content: str) -> str:
    """去掉网页脚本、样式和标签，只保留正文。"""
    content = re.sub(
        r"(?is)<(script|style|noscript)[^>]*>.*?</\1>",
        " ",
        content,
    )
    content = re.sub(r"(?s)<[^>]+>", " ", content)
    return html.unescape(content)


def load_text_file(path: str | Path) -> tuple[str, dict]:
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        raise NotImplementedError("PDF 解析尚未实现，下一步会引入 pypdf 或 pdfplumber。")

    content = file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix in {".html", ".htm"}:
        content = clean_html(content)

    metadata = {
        "source_path": str(file_path),
        "file_name": file_path.name,
        "file_type": suffix,
    }
    return content, metadata
