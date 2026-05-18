import json
import os
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_DIR / ".env")


def _storage_dir() -> Path:
    path = Path(os.getenv("SESSION_STORAGE_PATH", "storage/sessions"))
    if not path.is_absolute():
        path = BACKEND_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_path(session_id: str) -> Path:
    return _storage_dir() / f"{_safe_session_id(session_id)}.json"


def _safe_session_id(session_id: str) -> str:
    safe_id = "".join(ch for ch in (session_id or "") if ch.isalnum() or ch in "-_")
    if not safe_id or safe_id != session_id:
        raise KeyError("Invalid session ID.")
    return safe_id


def create_session(
    raw_email_thread: str,
    emails: list[dict],
    detected_category: str = "",
    selected_category: str = "",
    prompt: str = "",
) -> dict:
    session = {
        "sessionId": str(uuid4()),
        "rawEmailThread": raw_email_thread,
        "emails": emails,
        "detectedCategory": detected_category,
        "selectedCategory": selected_category or detected_category,
        "prompt": prompt,
        "generatedReply": "",
    }
    save_session(session)
    return session


def get_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if not path.exists():
        raise KeyError("Session not found.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise KeyError("Session data is invalid.") from exc


def save_session(session: dict) -> dict:
    _safe_session_id(session["sessionId"])
    path = _session_path(session["sessionId"])
    path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    return session


def reset_session(session_id: str) -> None:
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
