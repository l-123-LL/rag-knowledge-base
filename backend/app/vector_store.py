import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class VectorStore(Protocol):
    def add(
        self,
        id: str,
        text: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        ...

    def query(self, embedding: list[float], top_k: int = 5) -> list["VectorHit"]:
        ...

    def all_records(self) -> list["VectorRecord"]:
        ...


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

    def all_records(self) -> list[VectorRecord]:
        return list(self._records)

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


class FAISSVectorStore:
    """基于 FAISS 的本地向量库，支持保存和恢复。"""

    def __init__(self, dimensions: int, persist_dir: str | Path | None = None) -> None:
        import faiss

        self.dimensions = dimensions
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimensions))
        self._records: dict[int, VectorRecord] = {}
        self._next_id = 0

        if self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_if_exists()

    def add(
        self,
        id: str,
        text: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        import faiss
        import numpy as np

        internal_id = self._next_id
        self._next_id += 1
        self._records[internal_id] = VectorRecord(
            id=id,
            text=text,
            embedding=embedding,
            metadata=metadata or {},
        )
        vector = np.asarray([embedding], dtype="float32")
        ids = np.asarray([internal_id], dtype="int64")
        self.index.add_with_ids(vector, ids)

    def query(self, embedding: list[float], top_k: int = 5) -> list[VectorHit]:
        import numpy as np

        if self._next_id == 0:
            return []

        vector = np.asarray([embedding], dtype="float32")
        scores, indices = self.index.search(vector, min(top_k, self._next_id))
        hits: list[VectorHit] = []

        for score, index in zip(scores[0], indices[0]):
            if index < 0:
                continue
            record = self._records[int(index)]
            hits.append(
                VectorHit(
                    id=record.id,
                    text=record.text,
                    metadata=record.metadata,
                    score=float(score),
                )
            )

        return hits

    def all_records(self) -> list[VectorRecord]:
        return list(self._records.values())

    def save(self) -> None:
        if not self.persist_dir:
            return

        import faiss
        import json

        faiss.write_index(self.index, str(self.persist_dir / "index.faiss"))
        records = {
            str(internal_id): {
                "id": record.id,
                "text": record.text,
                "embedding": record.embedding,
                "metadata": record.metadata,
            }
            for internal_id, record in self._records.items()
        }
        (self.persist_dir / "records.json").write_text(
            json.dumps(records, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_if_exists(self) -> None:
        import faiss
        import json

        index_path = self.persist_dir / "index.faiss"
        records_path = self.persist_dir / "records.json"
        if not index_path.exists() or not records_path.exists():
            return

        self.index = faiss.read_index(str(index_path))
        records_data = json.loads(records_path.read_text(encoding="utf-8"))
        for internal_id, data in records_data.items():
            self._records[int(internal_id)] = VectorRecord(**data)
            self._next_id = max(self._next_id, int(internal_id) + 1)
