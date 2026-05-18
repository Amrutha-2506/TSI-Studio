from fastapi import APIRouter, HTTPException

from backend.models.schemas import GenerateReplyRequest, ReplyRegenerateRequest, ReplyResponse
from backend.services.category_prompts import detect_category, get_category_prompt, normalize_category
from backend.services.ai_generator import generate_reply, regenerate_reply
from backend.services.reply_quality import quality_check_reply, sanitize_reply
from backend.services.session_manager import get_session, save_session

router = APIRouter()


@router.post("/generate", response_model=ReplyResponse)
def generate(request: GenerateReplyRequest):
    session = None
    emails = request.emails
    if request.sessionId:
        try:
            session = get_session(request.sessionId)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Session not found.") from exc
        emails = session.get("emails", [])
    emails = _ordered_emails(emails)

    selected_category = normalize_category(
        request.selectedCategory
        or (session or {}).get("selectedCategory")
        or (session or {}).get("detectedCategory")
        or detect_category("", emails)
    )
    agent_instructions = request.agentInstructions or request.prompt or get_category_prompt(selected_category)

    try:
        reply = generate_reply(
            emails,
            selected_category,
            agent_instructions,
            request.accountData,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reply = sanitize_reply(reply)
    quality_check = quality_check_reply(reply, emails, request.accountData, selected_category)
    if session is not None:
        session["selectedCategory"] = selected_category
        session["prompt"] = agent_instructions
        session["accountData"] = request.accountData
        session["generatedReply"] = reply
        session["qualityCheck"] = quality_check
        save_session(session)
    return {"reply": reply, "qualityCheck": quality_check}


@router.post("/regenerate", response_model=ReplyResponse)
def regenerate(request: ReplyRegenerateRequest):
    session = None
    emails = request.emails
    if request.sessionId:
        try:
            session = get_session(request.sessionId)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Session not found.") from exc
        emails = session.get("emails", [])
    emails = _ordered_emails(emails)

    selected_category = normalize_category(
        request.selectedCategory
        or (session or {}).get("selectedCategory")
        or (session or {}).get("detectedCategory")
        or detect_category("", emails)
    )
    agent_instructions = request.agentInstructions or (session or {}).get("prompt") or get_category_prompt(selected_category)
    account_data = request.accountData or (session or {}).get("accountData", {})

    try:
        reply = regenerate_reply(
            emails,
            selected_category,
            agent_instructions,
            account_data,
            request.previousReply or (session or {}).get("generatedReply", ""),
            request.regenerationInstruction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reply = sanitize_reply(reply)
    quality_check = quality_check_reply(reply, emails, account_data, selected_category)
    if session is not None:
        session["selectedCategory"] = selected_category
        session["prompt"] = agent_instructions
        session["accountData"] = account_data
        session["generatedReply"] = reply
        session["qualityCheck"] = quality_check
        save_session(session)
    return {"reply": reply, "qualityCheck": quality_check}


def _ordered_emails(emails: list[dict]) -> list[dict]:
    return sorted(
        emails or [],
        key=lambda email: (
            _position_value(email.get("position") or email.get("id")),
            email.get("date") or email.get("timestamp") or "",
        ),
    )


def _position_value(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
