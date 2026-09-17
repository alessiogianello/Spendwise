import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.agent.orchestrator import get_or_create_session, stream_agent_turn
from app.config import get_settings
from app.db import get_db
from app.models import ConversationMessage, ConversationSession
from app.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    session = get_or_create_session(db, settings.demo_user_id, request.session_id)

    async def event_generator():
        async for event in stream_agent_turn(db, settings.demo_user_id, session.id, request.message):
            yield {"event": event["event"], "data": json.dumps(event["data"], default=str)}

    return EventSourceResponse(event_generator())


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    rows = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == settings.demo_user_id)
        .order_by(ConversationSession.started_at.desc())
        .all()
    )
    return [{"id": s.id, "title": s.title, "started_at": s.started_at} for s in rows]


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    """Returns raw content blocks per turn; the Flutter client applies the same
    text/tool_use/tool_result parsing it uses for the live SSE stream."""
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.id)
        .all()
    )
    return [
        {"role": r.role, "content": json.loads(r.content_json), "created_at": r.created_at}
        for r in rows
    ]
