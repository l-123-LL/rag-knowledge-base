from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: str | None = None
    # 默认 rag，保持升级前行为；tools 走可选的最小工具工作流。
    workflow_mode: Literal["rag", "tools"] = "rag"
    # 按生效时间检索（ISO 日期，默认今天）：用于"当时的政策是什么"这类问题。
    as_of: str | None = None


class IngestRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str = Field(default="示例资料", min_length=1)
    # 知识版本与生效时间：同一 doc_key 只保留最高版本，超出时间窗口的不参与检索。
    version: int = Field(default=1, ge=1)
    doc_key: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None


class UrlIngestRequest(BaseModel):
    url: str = Field(min_length=1)


class SessionResetRequest(BaseModel):
    session_id: str


class FaqCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    source: str = Field(default="人工录入", min_length=1)


class FaqUpdateRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(min_length=1)
    rating: Literal["up", "down"]
    comment: str | None = None


class TicketCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None
    reason: str = Field(default="customer_service", min_length=1)


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    decided_by: str | None = None
    # 驳回理由（可选）：记进审批单，便于审计与后续复盘。
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
    # tools 模式下附带执行轨迹，rag 模式下为 None，保持向后兼容。
    trace_id: str | None = None
    steps: list[dict] | None = None


class Source(BaseModel):
    id: str
    title: str
    category: str
    url: str
    status: Literal["indexed", "pending", "failed"]
    updatedAt: str
    description: str
    archived: bool = False
    tenant_id: str = "default"


class HealthResponse(BaseModel):
    status: str
