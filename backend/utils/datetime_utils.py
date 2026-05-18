from datetime import datetime
import re


DATE_PATTERNS = [
    "%d %b %Y, %I:%M %p",
    "%d %B %Y, %I:%M %p",
    "%d %b %Y, %I:%M:%S %p",
    "%d %B %Y, %I:%M:%S %p",
    "%d %b %Y %I:%M %p",
    "%d %B %Y %I:%M %p",
    "%d %b %Y %I:%M:%S %p",
    "%d %B %Y %I:%M:%S %p",
    "%b %d, %Y, %I:%M %p",
    "%B %d, %Y, %I:%M %p",
    "%b %d, %Y, %I:%M:%S %p",
    "%B %d, %Y, %I:%M:%S %p",
    "%b %d, %Y %I:%M %p",
    "%B %d, %Y %I:%M %p",
    "%b %d, %Y %I:%M:%S %p",
    "%B %d, %Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%y %I:%M %p",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%y %I:%M:%S %p",
    "%Y-%m-%d %H:%M",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y-%m-%d",
]


DATE_REGEXES = [
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)\b",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)\b",
    r"\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\b",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
]


def find_datetime_text(text: str) -> str | None:
    for pattern in DATE_REGEXES:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(0).replace("  ", " ").strip()
    return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", " ", value.replace(",", ", ")).strip()
    normalized = re.sub(
        r"^(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?),\s*",
        "",
        normalized,
        flags=re.I,
    )
    normalized = re.sub(r"\s+at\s+", " ", normalized, flags=re.I)
    normalized = re.sub(r"\s+(?:ET|EST|EDT|CT|CST|CDT|PT|PST|PDT)\b", "", normalized)
    normalized = re.sub(r",\s+", ", ", normalized)
    candidates = {value.strip(), normalized, normalized.replace(",", "")}
    for candidate in candidates:
        for pattern in DATE_PATTERNS:
            try:
                return datetime.strptime(candidate, pattern)
            except ValueError:
                continue
    return None


def format_timestamp(value: datetime | None, fallback: str | None = None) -> str:
    if value:
        return value.strftime("%d %b %Y, %I:%M %p").lstrip("0")
    return fallback or "Unknown"
