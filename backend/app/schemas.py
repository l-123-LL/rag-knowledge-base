from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: str | None = None


class IngestRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = Field(default="示例资料", min_length=1)


class UrlIngestRequest(BaseModel):
    url: str = Field(min_length=1)


class SessionResetRequest(BaseModel):
    session_id: str


class FaqCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    source: str = Field(default="人工录入", min_length=1)


class FeedbackRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(min_length=1)
    rating: Literal["up", "down"]
    comment: str | None = None


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
    latency_ms: int = 0
    usage: dict[str, int] | None = None
    cost: float | None = None


class Source(BaseModel):
    id: str
    title: str
    category: str
    url: str
    status: Literal["indexed", "pending", "failed"]
    updatedAt: str
    description: str
    archived: bool = False


class HealthResponse(BaseModel):
    status: str
