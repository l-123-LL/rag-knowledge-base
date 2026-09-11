from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .mock_data import find_mock_answer, sources
from .schemas import AskRequest, AskResponse, HealthResponse, Source

app = FastAPI(title="Medical RAG API", version="0.1.0")

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/sources", response_model=list[Source])
def list_sources() -> list[Source]:
    return sources


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    match = find_mock_answer(request.question)

    if match is None:
        return AskResponse(
            answer="当前示例资料不足，暂时无法给出可靠回答。",
            citations=[],
            model="mock",
            status="insufficient",
        )

    return AskResponse(
        answer=match["answer"],
        citations=match["citations"],
        model="mock",
        status="done",
    )
