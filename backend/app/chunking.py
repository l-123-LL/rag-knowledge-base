import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


DEFAULT_CHUNK_SIZE = 600
DEFAULT_OVERLAP = 80
DEFAULT_PARENT_SIZE = 1200
DEFAULT_CHILD_SIZE = 400


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


def split_text_hierarchical(
    text: str,
    parent_size: int = DEFAULT_PARENT_SIZE,
    child_size: int = DEFAULT_CHILD_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """父块 + 子块切分：子块用于检索（粒度细、命中准），父块用于生成（上下文完整）。

    父块文本直接写进子块 metadata，避免再引入一层存储；代价是索引文件会变大
    （每个子块都带一份父块文本），单机小库可以接受。
    """
    children: list[Chunk] = []
    parents = split_text(text, chunk_size=parent_size, overlap=0)

    for parent_index, parent in enumerate(parents):
        parent_id = f"parent-{parent_index}"
        for child_index, child in enumerate(
            split_text(parent.text, chunk_size=child_size, overlap=overlap)
        ):
            metadata = dict(child.metadata)
            metadata.update(
                {
                    "parent_id": parent_id,
                    "parent_text": parent.text,
                    "child_index": child_index,
                }
            )
            children.append(Chunk(text=child.text, metadata=metadata))

    return children
