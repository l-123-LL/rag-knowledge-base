import hashlib
import math
import re
from typing import Protocol


def tokenize(text: str) -> list[str]:
    """把中文拆成单字，英文和数字作为连续词元，适合轻量关键词匹配。"""
    return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower())


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """把文本列表转换为向量列表。"""


class HashEmbedder:
    """测试用的确定性向量，不依赖模型，也不会把测试变慢。"""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []

        for text in texts:
            vector = [0.0] * self.dimensions

            for token in tokenize(text):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[index] += sign

            norm = math.sqrt(sum(value * value for value in vector))
            if norm > 0:
                vector = [value / norm for value in vector]

            vectors.append(vector)

        return vectors
