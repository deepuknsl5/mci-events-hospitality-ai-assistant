from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.rag.retriever import EventRetriever
from app.services.chat_service import ChatService

retriever: EventRetriever | None = None
chat_service: ChatService | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever, chat_service
    retriever = EventRetriever()
    if retriever.collection.count() == 0:
        retriever.ingest()
    chat_service = ChatService(retriever)
    yield

app = FastAPI(
    title="MCI Events & Hospitality Assistant",
    version="1.0.0",
    description="Local-first, event-isolated RAG assistant prototype.",
    lifespan=lifespan,
)

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    event_id: str = Field(pattern=r"^event_[ab]$")
    message: str = Field(min_length=1, max_length=2000)
    booking_id: str | None = Field(default=None, max_length=100)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        return chat_service.chat(
            session_id=request.session_id,
            event_id=request.event_id,
            message=request.message,
            booking_id=request.booking_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
