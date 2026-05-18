from fastapi import APIRouter, HTTPException

from backend.models.schemas import AddEmailRequest, EmailListResponse, ParseEmailRequest
from backend.services.category_prompts import detect_category, get_category_prompt, normalize_category
from backend.services.email_parser import parse_email_thread
from backend.services.session_manager import create_session, get_session, save_session

router = APIRouter()


@router.post("/parse", response_model=EmailListResponse)
def parse_email(request: ParseEmailRequest):
    try:
        emails = parse_email_thread(request.emailThread)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    detected_category = detect_category(request.emailThread, emails)
    selected_category = normalize_category(request.selectedCategory or detected_category)
    prompt = request.agentInstructions.strip() or get_category_prompt(selected_category)
    session = create_session(
        request.emailThread,
        emails,
        detected_category=detected_category,
        selected_category=selected_category,
        prompt=prompt,
    )
    return session


@router.post("/add", response_model=EmailListResponse)
def add_email(request: AddEmailRequest):
    try:
        session = get_session(request.sessionId)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found.") from exc

    raw_thread = f"{session.get('rawEmailThread', '')}\n\n---\n\n{request.emailContent}"
    try:
        emails = parse_email_thread(raw_thread)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session["rawEmailThread"] = raw_thread
    session["emails"] = emails
    session["detectedCategory"] = detect_category(raw_thread, emails)
    session["selectedCategory"] = session.get("selectedCategory") or session["detectedCategory"]
    save_session(session)
    return session
