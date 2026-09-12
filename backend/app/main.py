import json
import time
import os
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException

from . import config  # noqa: F401
from .backup import create_backup
from .factory import build_pipeline
from .cost import calculate_cost
from .generation import GenerationError
from .ingestion import fetch_url_text, load_bytes
from .intent import classify_intent
from .observability import (
    log_ask_event,
    log_feedback,
    summarize_ask_log,
    summarize_feedback,
)
from .mock_data import add_faq, faq_count, faq_items, find_mock_answer, sources
from .pipeline import RAGPipeline
from .schemas import (
    AskRequest,
    AskResponse,
    Citation,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    FaqCreateRequest,
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
from .security import require_admin_key
from .ticket_store import count_tickets, create_ticket, list_tickets

app = FastAPI(title="Enterprise Customer Service RAG API", version="0.1.0")
app.state.pipeline: RAGPipeline | None = None
_request_times: dict[str, deque] = defaultdict(deque)

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/sources", response_model=list[Source])
def list_sources() -> list[Source]:
    return sources


@app.post("/ingest", response_model=IngestResponse)
def ingest(
    request: IngestRequest,
    _: None = Depends(require_admin_key),
) -> IngestResponse:
    pipeline = get_pipeline()
    chunk_count = pipeline.ingest_text(
        request.text,
        metadata={"source": request.source},
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
        )
    )
    return IngestResponse(chunk_count=chunk_count)


@app.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    _: None = Depends(require_admin_key),
) -> IngestResponse:
    content = await file.read()
    text, metadata = load_bytes(file.filename or "upload.txt", content)
    pipeline = get_pipeline()
    chunk_count = pipeline.ingest_text(
        text,
        metadata={"source": metadata["file_name"], "file_name": metadata["file_name"]},
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
        )
    )
    return IngestResponse(chunk_count=chunk_count)


@app.post("/ingest/url", response_model=IngestResponse)
def ingest_url(
    request: UrlIngestRequest,
    _: None = Depends(require_admin_key),
) -> IngestResponse:
    text, metadata = fetch_url_text(request.url)
    pipeline = get_pipeline()
    chunk_count = pipeline.ingest_text(
        text,
        metadata={"source": request.url, "file_name": request.url},
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
        )
    )
    return IngestResponse(chunk_count=chunk_count)


@app.post("/session/reset")
def reset_session(request: SessionResetRequest) -> dict:
    clear_session(request.session_id)
    return {"status": "ok"}


@app.get("/stats")
def stats() -> dict:
    pipeline = app.state.pipeline
    return {
        "source_count": len(sources),
        "chunk_count": pipeline.chunk_count() if pipeline else 0,
        "session_count": count_sessions(),
        "faq_count": faq_count(),
        "ticket_count": count_tickets(),
    }


@app.get("/metrics")
def metrics() -> dict:
    return {
        **summarize_ask_log(),
        **summarize_feedback(),
    }


@app.post("/sources/{source_id}/archive", response_model=Source)
def archive_source(
    source_id: str,
    archived: bool = True,
    _: None = Depends(require_admin_key),
) -> Source:
    for source in sources:
        if source.id == source_id:
            source.archived = archived
            return source
    raise HTTPException(status_code=404, detail="来源不存在")


@app.get("/faqs")
def list_faqs() -> list[dict]:
    return faq_items


@app.post("/faqs")
def create_faq(
    request: FaqCreateRequest,
    _: None = Depends(require_admin_key),
) -> dict:
    return add_faq(
        question=request.question,
        answer=request.answer,
        keywords=request.keywords,
        source=request.source,
    )


@app.post("/feedback")
def feedback(request: FeedbackRequest) -> dict:
    log_feedback(
        {
            "session_id": request.session_id,
            "question": request.question,
            "rating": request.rating,
            "comment": request.comment,
        }
    )
    return {"status": "ok"}


@app.post("/tickets")
def create_ticket_endpoint(request: TicketCreateRequest) -> dict:
    return create_ticket(
        question=request.question,
        session_id=request.session_id,
        reason=request.reason,
    )


@app.get("/tickets")
def get_tickets(limit: int = 100) -> list[dict]:
    return list_tickets(limit=limit)


@app.post("/backup")
def backup(_: None = Depends(require_admin_key)) -> dict:
    archive = create_backup()
    return {"archive": str(archive)}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    intent = classify_intent(request.question)
    if intent.intent != "knowledge":
        ticket = create_ticket(
            question=request.question,
            session_id=request.session_id,
            reason=intent.intent,
        )
        answer_text = (
            f"{intent.message or '已转接人工客服。'}"
            f"（工单号：{ticket['id']}）"
        )
        record_message(request.session_id, "user", request.question)
        record_message(request.session_id, "assistant", answer_text)
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

    faq_match = find_mock_answer(request.question)
    if faq_match is not None:
        record_message(request.session_id, "user", request.question)
        record_message(request.session_id, "assistant", faq_match["answer"])
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
    archived_sources = {source.title for source in sources if source.archived}

    try:
        history = get_history(request.session_id)
        result = pipeline.answer(
            request.question,
            top_k=request.top_k,
            history=history,
            exclude_sources=archived_sources,
        )
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    latency_ms = int((time.perf_counter() - started_at) * 1000)

    if not result.contexts:
        record_message(request.session_id, "user", request.question)
        record_message(
            request.session_id,
            "assistant",
            "当前示例资料不足，暂时无法给出可靠回答。",
        )
        log_ask_event(
            {
                "route": "rag",
                "session_id": request.session_id,
                "question": request.question,
                "model": "deepseek-chat",
                "status": "insufficient",
                "latency_ms": latency_ms,
            }
        )
        return AskResponse(
            answer="当前示例资料不足，暂时无法给出可靠回答。",
            citations=[],
            model="deepseek-chat",
            status="insufficient",
            latency_ms=latency_ms,
        )

    record_message(request.session_id, "user", request.question)
    record_message(request.session_id, "assistant", result.answer)
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
def ask_stream(request: AskRequest):
    pipeline = get_pipeline()
    history = get_history(request.session_id)
    archived_sources = {source.title for source in sources if source.archived}
    contexts = pipeline.retrieve(
        request.question,
        top_k=request.top_k,
        exclude_sources=archived_sources,
    )

    if not contexts:
        return JSONResponse(
            status_code=200,
            content={
                "answer": "当前资料不足，暂时无法给出可靠回答。",
                "citations": [],
                "status": "insufficient",
            },
        )

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
        yield f"data: {json.dumps({'type': 'sources', 'contexts': context_payload}, ensure_ascii=False)}\n\n"
        try:
            for delta in generator(request.question, contexts, history):
                yield f"data: {json.dumps({'type': 'delta', 'text': delta}, ensure_ascii=False)}\n\n"
        except GenerationError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
