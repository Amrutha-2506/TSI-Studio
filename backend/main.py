import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(BACKEND_DIR / ".env")

from backend.logging_config import configure_logging
from backend.models.schemas import EmailListResponse, ReplyResponse
from backend.routes.email_routes import add_email, parse_email
from backend.routes.email_routes import router as email_router
from backend.routes.reply_routes import generate as generate_reply_endpoint
from backend.routes.reply_routes import regenerate as regenerate_reply_endpoint
from backend.routes.reply_routes import router as reply_router
from backend.routes.session_routes import router as session_router

LOG_FILE = configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="TSI Studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://tsi-studio.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def log_startup():
    logger.info("TSI Studio API started. Logs are writing to %s", LOG_FILE)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    logger.info("Request started: %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "Request failed: %s %s duration=%.2fms",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "Request finished: %s %s status=%s duration=%.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

app.include_router(email_router, prefix="/api/email", tags=["email"])
app.include_router(reply_router, prefix="/api/reply", tags=["reply"])
app.include_router(session_router, prefix="/api/session", tags=["session"])

app.add_api_route(
    "/api/parse-email-thread",
    parse_email,
    methods=["POST"],
    response_model=EmailListResponse,
    tags=["email"],
)
app.add_api_route(
    "/api/add-email",
    add_email,
    methods=["POST"],
    response_model=EmailListResponse,
    tags=["email"],
)
app.add_api_route(
    "/api/generate-reply",
    generate_reply_endpoint,
    methods=["POST"],
    response_model=ReplyResponse,
    tags=["reply"],
)
app.add_api_route(
    "/api/regenerate-reply",
    regenerate_reply_endpoint,
    methods=["POST"],
    response_model=ReplyResponse,
    tags=["reply"],
)


@app.get("/")
def home():
    return {"message": "TSI Studio backend is running"}


@app.get("/health")
def health():
    return {"status": "ok", "cors": "updated"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
