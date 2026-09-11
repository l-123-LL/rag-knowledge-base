import math
from dataclasses import dataclass, field


@dataclass
class VectorRecord:
    id: str
    text: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)


@dataclass
class VectorHit:
    id: str
    text: str
    metadata: dict
    score: float


class InMemoryVectorStore:
    """先用内存实现验证流程，后续再替换为 Chroma。"""

    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def add(
        self,
        id: str,
        text: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        self._records.append(
            VectorRecord(
                id=id,
                text=text,
                embedding=embedding,
                metadata=metadata or {},
            )
        )

    def query(self, embedding: list[float], top_k: int = 5) -> list[VectorHit]:
        hits: list[VectorHit] = []

        for record in self._records:
            score = self._cosine(embedding, record.embedding)
            hits.append(
                VectorHit(
                    id=record.id,
                    text=record.text,
                    metadata=record.metadata,
                    score=score,
                )
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0

        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))

        if left_norm == 0 or right_norm == 0:
            return 0.0

        return dot / (left_norm * right_norm)
