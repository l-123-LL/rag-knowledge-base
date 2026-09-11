import time
import os

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from . import config  # noqa: F401
from .factory import build_pipeline
from .cost import calculate_cost
from .generation import GenerationError
from .ingestion import load_bytes
from .mock_data import sources
from .pipeline import RAGPipeline
from .schemas import (
    AskRequest,
    AskResponse,
    Citation,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    Source,
)

app = FastAPI(title="Medical RAG API", version="0.1.0")
app.state.pipeline: RAGPipeline | None = None

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
def ingest(request: IngestRequest) -> IngestResponse:
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
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
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


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    pipeline = get_pipeline()
    started_at = time.perf_counter()

    try:
        result = pipeline.answer(request.question, top_k=request.top_k)
    except GenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    latency_ms = int((time.perf_counter() - started_at) * 1000)

    if not result.contexts:
        return AskResponse(
            answer="当前示例资料不足，暂时无法给出可靠回答。",
            citations=[],
            model="deepseek-chat",
            status="insufficient",
            latency_ms=latency_ms,
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
        cost=calculate_cost(
            result.usage,
            input_price_per_million=float(
                os.getenv("DEEPSEEK_INPUT_PRICE_PER_MILLION", "0")
            ),
            output_price_per_million=float(
                os.getenv("DEEPSEEK_OUTPUT_PRICE_PER_MILLION", "0")
            ),
        ),
    )
