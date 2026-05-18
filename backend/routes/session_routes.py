from fastapi import APIRouter, HTTPException

from backend.models.schemas import SessionResetRequest, SessionResetResponse, SessionResponse
from backend.services.session_manager import get_session, reset_session

router = APIRouter()


@router.get("/{session_id}", response_model=SessionResponse)
def read_session(session_id: str):
    try:
        session = get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc
    return session


@router.post("/reset", response_model=SessionResetResponse)
def reset(request: SessionResetRequest):
    try:
        reset_session(request.sessionId)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc

    return {"success": True, "message": "Session cleared successfully"}
