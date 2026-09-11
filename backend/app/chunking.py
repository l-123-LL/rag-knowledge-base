import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


DEFAULT_CHUNK_SIZE = 600
DEFAULT_OVERLAP = 80


def normalize_text(text: str) -> str:
    """统一空白和换行，避免 PDF 或网页文本把段落切得太碎。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """按段落优先切分，超长段落再用重叠窗口切分。"""
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    normalized = normalize_text(text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized)]
    chunks: list[Chunk] = []

    for paragraph in paragraphs:
        if not paragraph:
            continue

        if len(paragraph) <= chunk_size:
            chunks.append(Chunk(text=paragraph))
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + chunk_size, len(paragraph))
            chunk = paragraph[start:end].strip()

            if chunk:
                chunks.append(Chunk(text=chunk))

            if end >= len(paragraph):
                break

            start = max(end - overlap, start + 1)

    return chunks
