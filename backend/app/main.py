import json
import hashlib
import logging
import time
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException

from . import config  # noqa: F401
from .backup import create_backup
from .approvals import get_approval, list_approvals, save_approval
from .factory import build_pipeline
from .cost import calculate_cost
from .generation import GenerationError
from .faq_store import (
    add_faq,
    delete_faq,
    faq_count,
    find_faq_answer,
    list_faqs as list_faq_store,
    update_faq,
)
from .ingestion import fetch_url_text, load_bytes
from .intent import classify_intent
from .observability import (
    log_ask_event,
    log_feedback,
    summarize_ask_log,
    summarize_feedback,
)
from .mock_data import sources
from .pipeline import RAGPipeline
from .trace_store import read_trace
from .workflow import run_tool_workflow
from .schemas import (
    AskRequest,
    AskResponse,
    ApprovalDecisionRequest,
    Citation,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    FaqCreateRequest,
    FaqUpdateRequest,
    FeedbackRequest,
    SessionResetRequest,
    Source,
    TicketCreateRequest,
    UrlIngestRequest,
)
from .session_store import (
    clear_session,
    count_sessions,
    get_history,
    record_message,
)
from .security import require_admin_key, require_user_token
from .tenant import get_tenant_id
from .ticket_store import count_tickets, create_ticket, list_tickets
from .tools import ToolContext, execute_tool

logger = logging.getLogger("rag.api")

app = FastAPI(title="Enterprise Customer Service RAG API", version="0.1.0")
app.state.pipeline: RAGPipeline | None = None
_request_times: dict[str, deque] = defaultdict(deque)


@app.on_event("startup")
def warn_on_missing_auth() -> None:
    """默认不强制鉴权，启动时明确提示，避免把演示配置直接搬上公网。"""
    if not os.getenv("OIDC_JWKS_URL") and not os.getenv("ADMIN_API_KEY"):
        logger.warning(
            "未配置 OIDC_JWKS_URL 或 ADMIN_API_KEY：问答接口当前对任何可访问者开放，"
            "生产环境请先配置鉴权或前置网关。"
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    if limit > 0 and request.url.path != "/health":
        client = request.client.host if request.client else "unknown"
        now = time.time()
        history = _request_times[client]
        while history and history[0] < now - 60:
            history.popleft()
        if len(history) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试"},
            )
        history.append(now)
    return await call_next(request)


def get_pipeline() -> RAGPipeline:
    if app.state.pipeline is None:
        app.state.pipeline = build_pipeline()
    return app.state.pipeline


# 拒答与转人工共用同一句话术来源，避免 /ask 与 /ask/stream 说法不一致。
INSUFFICIENT_ANSWER = "当前资料不足，暂时无法确认答案。"
INSUFFICIENT_ESCALATION = "当前资料不足，暂时无法确认答案，已为您转交人工客服跟进。"


def escalate_to_human(
    question: str,
    session_id: str | None,
    reason: str,
    tenant_id: str,
    prefix: str,
) -> str:
    """统一转人工出口：建工单并返回带工单号的引导话术。"""
    ticket = create_ticket(
        question=question,
        session_id=session_id,
        reason=reason,
        tenant_id=tenant_id,
    )
    return f"{prefix}（工单号：{ticket['id']}）"


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/sources", response_model=list[Source])
def list_sources(
    tenant_id: str = Depends(get_tenant_id),
) -> list[Source]:
    """来源列表：优先返回索引里真实存在的资料，索引为空时才退回示例列表。

    以前这里只返回内存里的示例列表，导入了真实资料也看不出来；而且列表随进程
    重启就丢。现在直接从索引元数据反推（不需要加载嵌入模型，读 records.json 即可）。
    """
    indexed = indexed_sources(app.state.pipeline)
    if indexed:
        return [source for source in indexed if source.tenant_id == tenant_id]
    return [source for source in sources if source.tenant_id == tenant_id]


def indexed_sources(pipeline) -> list[Source]:
    """按 source 字段聚合索引里的分块，得到「有哪些资料、各有多少分块」。"""
    chunks: list[tuple[dict, str]] = []
    retriever = getattr(pipeline, "retriever", None) if pipeline else None
    if retriever is not None and getattr(retriever, "doc_metadata", None):
        chunks = list(zip(retriever.doc_metadata, retriever.doc_texts))
    else:
        # 管线还没构建时读落盘记录，避免为了看资料列表就把模型加载起来
        records_path = Path(os.getenv("FAISS_DIR", "data/faiss")) / "records.json"
        if records_path.exists():
            try:
                records = json.loads(records_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                records = {}
            chunks = [
                (record.get("metadata") or {}, record.get("text") or "")
                for record in records.values()
            ]

    grouped: dict[tuple[str, str], dict] = {}
    for metadata, text in chunks:
        title = metadata.get("source") or metadata.get("file_name") or "未命名资料"
        tenant = metadata.get("tenant_id", "default")
        entry = grouped.setdefault(
            (tenant, title),
            {"count": 0, "url": metadata.get("url", ""), "sample": ""},
        )
        entry["count"] += 1
        if not entry["sample"]:
            entry["sample"] = " ".join((text or "").split())

    return [
        Source(
            # id 用内容摘要，保证重启后稳定（Python 内置 hash 每个进程都会变）
            id=f"indexed-{index}-{hashlib.sha1(title.encode('utf-8')).hexdigest()[:6]}",
            title=title,
            category="已入库资料",
            url=entry["url"],
            status="indexed",
            updatedAt="已入库",
            description=f"{entry['count']} 个分块"
            + (f"｜{entry['sample'][:60]}" if entry["sample"] else ""),
            tenant_id=tenant,
        )
        for index, ((tenant, title), entry) in enumerate(
            sorted(grouped.items(), key=lambda item: item[0][1])
        )
    ]


@app.post("/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> IngestResponse:
    pipeline = get_pipeline()
    # 版本与生效时间写进 chunk 元数据，检索时按 doc_key 取最高版本、按时间窗口过滤。
    ingest_metadata = {
        "source": request.source,
        "tenant_id": tenant_id,
        "version": request.version,
    }
    if request.doc_key:
        ingest_metadata["doc_key"] = request.doc_key
    if request.effective_from:
        ingest_metadata["effective_from"] = request.effective_from
    if request.effective_to:
        ingest_metadata["effective_to"] = request.effective_to

    chunk_count = pipeline.ingest_text(
        request.text,
        metadata=ingest_metadata,
    )
    sources.append(
        Source(
            id=f"ingested-{len(sources) + 1}",
            title=request.source,
            category="用户资料",
            url="",
            status="indexed",
            updatedAt="刚刚",
            description=request.text[:100],
            tenant_id=tenant_id,
        )
    )
    return IngestResponse(chunk_count=chunk_count)


@app.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> IngestResponse:
    content = await file.read()
    text, metadata = load_bytes(file.filename or "upload.txt", content)
    pipeline = get_pipeline()
    chunk_count = pipeline.ingest_text(
        text,
        metadata={
            "source": metadata["file_name"],
            "file_name": metadata["file_name"],
            "tenant_id": tenant_id,
        },
    )
    sources.append(
        Source(
            id=f"uploaded-{len(sources) + 1}",
            title=metadata["file_name"],
            category="上传资料",
            url="",
            status="indexed",
            updatedAt="刚刚",
            description=text[:100],
            tenant_id=tenant_id,
        )
    )
    return IngestResponse(chunk_count=chunk_count)


@app.post("/ingest/url", response_model=IngestResponse)
def ingest_url(
    request: UrlIngestRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> IngestResponse:
    text, metadata = fetch_url_text(request.url)
    pipeline = get_pipeline()
    chunk_count = pipeline.ingest_text(
        text,
        metadata={
            "source": request.url,
            "file_name": request.url,
            "tenant_id": tenant_id,
        },
    )
    sources.append(
        Source(
            id=f"url-{len(sources) + 1}",
            title=request.url,
            category="网页资料",
            url=request.url,
            status="indexed",
            updatedAt="刚刚",
            description=text[:100],
            tenant_id=tenant_id,
        )
    )
    return IngestResponse(chunk_count=chunk_count)


@app.post("/session/reset")
def reset_session(
    request: SessionResetRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    clear_session(request.session_id, tenant_id=tenant_id)
    return {"status": "ok"}


@app.get("/stats")
def stats(tenant_id: str = Depends(get_tenant_id)) -> dict:
    pipeline = app.state.pipeline
    chunk_count = pipeline.chunk_count() if pipeline else persisted_chunk_count()
    # 来源数跟着真实索引走，同样是"有真实资料就不看示例列表"
    indexed = indexed_sources(pipeline)
    source_count = (
        sum(1 for source in indexed if source.tenant_id == tenant_id)
        if indexed
        else sum(1 for source in sources if source.tenant_id == tenant_id)
    )
    return {
        "source_count": source_count,
        "chunk_count": chunk_count,
        "session_count": count_sessions(tenant_id=tenant_id),
        "faq_count": faq_count(tenant_id=tenant_id),
        "ticket_count": count_tickets(tenant_id=tenant_id),
    }


def persisted_chunk_count() -> int:
    records_path = Path(os.getenv("FAISS_DIR", "data/faiss")) / "records.json"
    if not records_path.exists():
        return 0
    try:
        return len(json.loads(records_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return 0


@app.get("/metrics")
def metrics() -> dict:
    return {
        **summarize_ask_log(),
        **summarize_feedback(),
    }


@app.get("/alerts")
def alerts() -> dict:
    metric_data = {
        **summarize_ask_log(),
        **summarize_feedback(),
    }
    latency_threshold = float(os.getenv("ALERT_LATENCY_MS", "5000"))
    helpful_threshold = float(os.getenv("ALERT_HELPFUL_RATE", "0.7"))
    active_alerts: list[dict] = []

    if metric_data["avg_latency_ms"] > latency_threshold:
        active_alerts.append(
            {
                "type": "latency",
                "message": "平均响应延迟超过阈值",
                "value": metric_data["avg_latency_ms"],
                "threshold": latency_threshold,
            }
        )

    if (
        metric_data["feedback_count"] > 0
        and metric_data["helpful_rate"] < helpful_threshold
    ):
        active_alerts.append(
            {
                "type": "helpful_rate",
                "message": "有帮助率低于阈值",
                "value": metric_data["helpful_rate"],
                "threshold": helpful_threshold,
            }
        )

    return {
        "status": "warning" if active_alerts else "ok",
        "alerts": active_alerts,
        "metrics": metric_data,
    }


@app.post("/sources/{source_id}/archive", response_model=Source)
def archive_source(
    source_id: str,
    archived: bool = True,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> Source:
    for source in sources:
        if source.id == source_id and source.tenant_id == tenant_id:
            source.archived = archived
            return source
    raise HTTPException(status_code=404, detail="来源不存在")


@app.get("/faqs")
def list_faqs(tenant_id: str = Depends(get_tenant_id)) -> list[dict]:
    return list_faq_store(tenant_id)


@app.post("/faqs")
def create_faq(
    request: FaqCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> dict:
    return add_faq(
        question=request.question,
        answer=request.answer,
        keywords=request.keywords,
        source=request.source,
        tenant_id=tenant_id,
    )


@app.put("/faqs/{faq_id}")
def edit_faq(
    faq_id: str,
    request: FaqUpdateRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> dict:
    item = update_faq(
        faq_id=faq_id,
        question=request.question,
        answer=request.answer,
        keywords=request.keywords,
        tenant_id=tenant_id,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    return item


@app.delete("/faqs/{faq_id}")
def remove_faq(
    faq_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> dict:
    if not delete_faq(faq_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="FAQ 不存在")
    return {"status": "ok"}


@app.post("/feedback")
def feedback(
    request: FeedbackRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    log_feedback(
        {
            "session_id": request.session_id,
            "question": request.question,
            "rating": request.rating,
            "comment": request.comment,
            "tenant_id": tenant_id,
        }
    )
    return {"status": "ok"}


@app.post("/tickets")
def create_ticket_endpoint(
    request: TicketCreateRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    return create_ticket(
        question=request.question,
        session_id=request.session_id,
        reason=request.reason,
        tenant_id=tenant_id,
    )


@app.get("/tickets")
def get_tickets(
    limit: int = 100,
    tenant_id: str = Depends(get_tenant_id),
) -> list[dict]:
    return list_tickets(limit=limit, tenant_id=tenant_id)


@app.get("/approvals")
def list_pending_approvals(
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> list[dict]:
    """高风险写操作的审批队列（管理员可见）。"""
    return list_approvals(tenant_id)


@app.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_admin_key),
) -> dict:
    """批准/驳回：批准后才真正执行工具，重复决策不会重复执行（幂等）。"""
    record = get_approval(approval_id, tenant_id=tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到该审批单")

    if record["status"] != "pending":
        return record

    record["decided_at"] = datetime.now(timezone.utc).isoformat()
    record["decided_by"] = request.decided_by or "admin"
    record["decision_comment"] = request.comment
    record["status"] = "approved" if request.approved else "rejected"

    if request.approved:
        context = ToolContext(
            tenant_id=tenant_id,
            session_id=record.get("session_id"),
            approved=True,
        )
        execution = execute_tool(record["tool"], record["payload"], context)
        record["execution"] = {
            "ok": execution.ok,
            "code": execution.code,
            "data": execution.data,
        }
        record["status"] = "executed" if execution.ok else "failed"

    save_approval(record)
    return record


@app.get("/traces/{trace_id}")
def get_trace(
    trace_id: str,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_user_token),
) -> dict:
    """按 trace_id 还原一次执行过程；轨迹按租户隔离。"""
    record = read_trace(trace_id)
    if record is None or record.get("tenant_id", "default") != tenant_id:
        raise HTTPException(status_code=404, detail="未找到该 trace")
    return record


@app.post("/backup")
def backup(_: None = Depends(require_admin_key)) -> dict:
    archive = create_backup()
    return {"archive": str(archive)}


def run_tools_mode(request: AskRequest, tenant_id: str) -> AskResponse:
    """工具工作流分支：复用同一套会话、租户、日志与成本统计。"""
    pipeline = get_pipeline()
    archived_sources = {
        source.title
        for source in sources
        if source.archived and source.tenant_id == tenant_id
    }
    history = get_history(request.session_id, tenant_id=tenant_id)

    try:
        outcome = run_tool_workflow(
            request.question,
            pipeline=pipeline,
            tenant_id=tenant_id,
            session_id=request.session_id,
            history=history,
            exclude_sources=archived_sources,
        )
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
    record_message(request.session_id, "assistant", outcome.answer, tenant_id=tenant_id)
    log_ask_event(
        {
            "route": "tools",
            "session_id": request.session_id,
            "question": request.question,
            "model": outcome.model,
            "status": outcome.status,
            "latency_ms": outcome.latency_ms,
            "usage": outcome.usage,
            "cost": outcome.cost,
            "citation_count": len(outcome.citations),
            "tool_calls": outcome.tool_calls,
            "trace_id": outcome.trace_id,
        }
    )

    return AskResponse(
        answer=outcome.answer,
        citations=outcome.citations,
        model=outcome.model,
        status=outcome.status,
        latency_ms=outcome.latency_ms,
        usage=outcome.usage,
        cost=outcome.cost,
        trace_id=outcome.trace_id,
        steps=outcome.steps,
    )


@app.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_user_token),
) -> AskResponse:
    # 可选工具工作流：与原有 rag 分支完全隔离，出问题把 workflow_mode 切回 rag 即可。
    if request.workflow_mode == "tools":
        return run_tools_mode(request, tenant_id)

    intent = classify_intent(request.question)
    if intent.intent != "knowledge":
        answer_text = escalate_to_human(
            question=request.question,
            session_id=request.session_id,
            reason=intent.intent,
            tenant_id=tenant_id,
            prefix=intent.message or "已为您转接人工客服，请稍候。",
        )
        record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
        record_message(
            request.session_id,
            "assistant",
            answer_text,
            tenant_id=tenant_id,
        )
        log_ask_event(
            {
                "route": "intent",
                "session_id": request.session_id,
                "question": request.question,
                "model": "intent",
            }
        )
        return AskResponse(
            answer=answer_text,
            citations=[],
            model="intent",
            status="done",
        )

    faq_match = find_faq_answer(request.question, tenant_id=tenant_id)
    if faq_match is not None:
        record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
        record_message(
            request.session_id,
            "assistant",
            faq_match["answer"],
            tenant_id=tenant_id,
        )
        log_ask_event(
            {
                "route": "faq",
                "session_id": request.session_id,
                "question": request.question,
                "model": "faq",
            }
        )
        return AskResponse(
            answer=faq_match["answer"],
            citations=faq_match["citations"],
            model="faq",
            status="done",
        )

    pipeline = get_pipeline()
    started_at = time.perf_counter()
    archived_sources = {
        source.title
        for source in sources
        if source.archived and source.tenant_id == tenant_id
    }

    try:
        history = get_history(request.session_id, tenant_id=tenant_id)
        result = pipeline.answer(
            request.question,
            top_k=request.top_k,
            history=history,
            exclude_sources=archived_sources,
            tenant_id=tenant_id,
            as_of=request.as_of,
        )
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    latency_ms = int((time.perf_counter() - started_at) * 1000)

    if not result.contexts:
        # 找不到可靠资料时不再只是拒答：建工单并引导转人工，避免用户卡在死循环里。
        answer_text = escalate_to_human(
            question=request.question,
            session_id=request.session_id,
            reason="insufficient_context",
            tenant_id=tenant_id,
            prefix=INSUFFICIENT_ESCALATION,
        )
        record_message(
            request.session_id,
            "user",
            request.question,
            tenant_id=tenant_id,
        )
        record_message(
            request.session_id,
            "assistant",
            answer_text,
            tenant_id=tenant_id,
        )
        log_ask_event(
            {
                "route": "rag",
                "session_id": request.session_id,
                "question": request.question,
                "model": "deepseek-chat",
                "status": "insufficient",
                "escalated": True,
                "latency_ms": latency_ms,
            }
        )
        return AskResponse(
            answer=answer_text,
            citations=[],
            model="deepseek-chat",
            status="insufficient",
            latency_ms=latency_ms,
        )

    record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
    record_message(
        request.session_id,
        "assistant",
        result.answer,
        tenant_id=tenant_id,
    )
    cost = calculate_cost(
        result.usage,
        input_price_per_million=float(
            os.getenv("DEEPSEEK_INPUT_PRICE_PER_MILLION", "0")
        ),
        output_price_per_million=float(
            os.getenv("DEEPSEEK_OUTPUT_PRICE_PER_MILLION", "0")
        ),
    )
    log_ask_event(
        {
            "route": "rag",
            "session_id": request.session_id,
            "question": request.question,
            "model": "deepseek-chat",
            "status": "done",
            "latency_ms": latency_ms,
            "usage": result.usage,
            "cost": cost,
            "citation_count": len(result.contexts),
        }
    )
    return AskResponse(
        answer=result.answer,
        citations=[
            Citation(
                id=str(index),
                title=context.metadata.get("source", "未知来源"),
                url=context.metadata.get("url", ""),
                location=context.metadata.get("file_name", ""),
                snippet=context.text[:200],
                score=context.combined_score,
            )
            for index, context in enumerate(result.contexts)
        ],
        model="deepseek-chat",
        status="done",
        latency_ms=latency_ms,
        usage=result.usage,
        cost=cost,
    )


@app.post("/ask/stream")
def ask_stream(
    request: AskRequest,
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_user_token),
):
    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def text_stream(text: str, contexts: list[dict] | None = None):
        yield sse({"type": "sources", "contexts": contexts or []})
        yield sse({"type": "delta", "text": text})
        yield "data: [DONE]\n\n"

    # 工具工作流在流式接口里同样可用：先跑完工作流，再一次性吐出结果。
    if request.workflow_mode == "tools":
        outcome = run_tools_mode(request, tenant_id)
        return StreamingResponse(
            text_stream(
                outcome.answer,
                [item.model_dump() for item in outcome.citations],
            ),
            media_type="text/event-stream",
        )

    intent = classify_intent(request.question)
    if intent.intent != "knowledge":
        text = escalate_to_human(
            question=request.question,
            session_id=request.session_id,
            reason=intent.intent,
            tenant_id=tenant_id,
            prefix=intent.message or "已为您转接人工客服，请稍候。",
        )
        record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
        record_message(
            request.session_id,
            "assistant",
            text,
            tenant_id=tenant_id,
        )
        return StreamingResponse(text_stream(text), media_type="text/event-stream")

    faq_match = find_faq_answer(request.question, tenant_id=tenant_id)
    if faq_match is not None:
        record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
        record_message(
            request.session_id,
            "assistant",
            faq_match["answer"],
            tenant_id=tenant_id,
        )
        return StreamingResponse(
            text_stream(faq_match["answer"]),
            media_type="text/event-stream",
        )

    pipeline = get_pipeline()
    history = get_history(request.session_id, tenant_id=tenant_id)
    archived_sources = {
        source.title
        for source in sources
        if source.archived and source.tenant_id == tenant_id
    }
    contexts = pipeline.retrieve(
        request.question,
        top_k=request.top_k,
        exclude_sources=archived_sources,
        tenant_id=tenant_id,
    )

    if not contexts:
        # 流式路径保持与 /ask 一致：资料不足同样建单并引导转人工。
        text = escalate_to_human(
            question=request.question,
            session_id=request.session_id,
            reason="insufficient_context",
            tenant_id=tenant_id,
            prefix=INSUFFICIENT_ESCALATION,
        )
        record_message(request.session_id, "user", request.question, tenant_id=tenant_id)
        record_message(
            request.session_id,
            "assistant",
            text,
            tenant_id=tenant_id,
        )
        return StreamingResponse(text_stream(text), media_type="text/event-stream")

    generator = getattr(pipeline.generator, "stream", None)
    if generator is None:
        raise HTTPException(status_code=501, detail="当前生成器不支持流式输出")

    context_payload = [
        {
            "text": context.text,
            "source": context.metadata.get("source", "未知来源"),
            "score": context.combined_score,
        }
        for context in contexts
    ]

    def event_stream():
        yield sse({"type": "sources", "contexts": context_payload})
        try:
            for delta in generator(request.question, contexts, history):
                yield sse({"type": "delta", "text": delta})
        except GenerationError as exc:
            yield sse({"type": "error", "message": str(exc)})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
