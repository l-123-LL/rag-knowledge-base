import html
import re
from io import BytesIO
from pathlib import Path

import httpx


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
    content = file_path.read_bytes()
    return load_bytes(file_path.name, content)


def load_bytes(filename: str, content: bytes) -> tuple[str, dict]:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        text = "\n\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        metadata = {
            "source_path": filename,
            "file_name": filename,
            "file_type": suffix,
        }
        return text, metadata

    text = content.decode("utf-8", errors="ignore")

    if suffix in {".html", ".htm"}:
        text = clean_html(text)

    metadata = {
        "source_path": filename,
        "file_name": filename,
        "file_type": suffix,
    }
    return text, metadata


def fetch_url_text(url: str, timeout_seconds: float = 20.0) -> tuple[str, dict]:
    """抓取公开网页并清洗正文；尊重服务端错误，但不做 JavaScript 渲染。"""
    response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    text = clean_html(response.text)
    metadata = {
        "source_path": url,
        "file_name": url,
        "file_type": ".html",
    }
    return text, metadata
