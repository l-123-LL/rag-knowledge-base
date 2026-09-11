from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class IngestRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = Field(default="示例资料", min_length=1)


class IngestResponse(BaseModel):
    chunk_count: int


class Citation(BaseModel):
    id: str
    title: str
    url: str
    location: str
    snippet: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str
    status: Literal["done", "insufficient"]


class Source(BaseModel):
    id: str
    title: str
    category: str
    url: str
    status: Literal["indexed", "pending", "failed"]
    updatedAt: str
    description: str


class HealthResponse(BaseModel):
    status: str
