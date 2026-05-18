import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_LOG_FILE = BACKEND_DIR / "logs" / "app.log"


def configure_logging() -> Path:
    log_file = Path(os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE))).resolve()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(os.getenv("LOG_MAX_BYTES", "1048576")),
        backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        encoding="utf-8",
    )
    file_handler.set_name("tsi_file_handler")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    _replace_file_handler(root_logger, file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = False
        _replace_file_handler(logger, file_handler)

    return log_file


def _replace_file_handler(logger: logging.Logger, file_handler: RotatingFileHandler) -> None:
    for handler in list(logger.handlers):
        if handler.get_name() == "tsi_file_handler":
            logger.removeHandler(handler)
            handler.close()
    logger.addHandler(file_handler)
