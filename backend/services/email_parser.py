import re

from backend.services.chronology_sorter import sort_chronologically
from backend.utils.datetime_utils import find_datetime_text, format_timestamp, parse_datetime
from backend.utils.preview_generator import make_preview
from backend.utils.text_cleaner import clean_text, strip_email_headers


MIN_THREAD_LENGTH = 20
MAX_THREAD_LENGTH = 100000
GNG_PATTERNS = (
    "gng customer service",
    "gng customer care",
    "georgia natural gas",
    "customerservice@gng.com",
    "customerservice@gngcs.com",
    "do_not_reply@gng.com",
    "gngemail@response.gng.com",
    "response.gng.com",
    "mail.gng.com",
    "@gng.com",
    "@gngcs.com",
)
IGNORED_BODY_LINE_PATTERNS = (
    re.compile(r"Get Outlook for iOS", re.I),
    re.compile(r"Yahoo Mail: Search, Organize, Conquer", re.I),
    re.compile(r"VIEW\s*&\s*PAY\s+NOW", re.I),
    re.compile(r"cid:image[^\s]*", re.I),
)
ADDRESS_PATTERN = re.compile(
    r"\b\d{2,6}\s+[A-Za-z0-9 .'-]+(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|court|ct|circle|cir|trail|trl|way|place|pl|close|sw|se|nw|ne)\b",
    re.I,
)


def parse_email_thread(raw_thread: str) -> list[dict]:
    text = clean_text(raw_thread)
    if not text:
        raise ValueError("Email thread cannot be empty.")
    if len(text) < MIN_THREAD_LENGTH:
        raise ValueError("Email thread is too short to parse.")
    if len(text) > MAX_THREAD_LENGTH:
        raise ValueError("Email thread is too large to parse.")

    chunks = _split_thread(text)
    parsed = []
    for index, chunk in enumerate(chunks):
        email = _parse_chunk(chunk, index)
        if email["body"]:
            parsed.append(email)

    if not parsed:
        parsed.append(_parse_chunk(text, 0))

    parsed = [email for email in parsed if len(email["body"]) >= MIN_THREAD_LENGTH]
    if not parsed:
        raise ValueError("Email thread does not contain enough readable email content.")

    parsed = sort_chronologically(parsed)

    output = []
    for position, email in enumerate(parsed, start=1):
        body = email["body"]
        timestamp = format_timestamp(email["_sortTimestamp"], email["date"])
        email_type = _email_type(email["senderType"])
        output.append(
            {
                "id": position,
                "position": position,
                "type": email_type,
                "sender": _sender_label(email["senderType"]),
                "senderType": email["senderType"],
                "from": email["from"],
                "fromName": email["fromName"],
                "to": email["to"],
                "subject": email["subject"],
                "date": email["date"] or timestamp,
                "timestamp": timestamp,
                "preview": make_preview(body),
                "body": body,
                "hasServiceAddress": bool(ADDRESS_PATTERN.search(body)),
            }
        )
    return output


def _split_thread(text: str) -> list[str]:
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if line.strip().lower().startswith("from:") and _has_complete_header_block(lines, index)
    ]

    if not starts:
        return [text]

    chunks = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        chunk = clean_text("\n".join(lines[start:end]))
        if chunk:
            chunks.append(chunk)
    return chunks


def _parse_chunk(chunk: str, index: int) -> dict:
    headers = _extract_headers(chunk)
    timestamp_text = headers.get("date") or headers.get("sent") or find_datetime_text(chunk)
    timestamp = parse_datetime(timestamp_text)
    body = _clean_email_body(strip_email_headers(_remove_label_prefix(chunk)))
    from_field = headers.get("from", "")
    from_name = _clean_name(from_field)
    sender_type = _detect_sender_type(from_field)

    return {
        "_originalIndex": index,
        "_sortTimestamp": timestamp,
        "senderType": sender_type,
        "from": from_field,
        "fromName": from_name or _sender_label(sender_type),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": timestamp_text or "",
        "body": body,
    }


def _extract_headers(chunk: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for label in ("from", "to", "sent", "date", "subject"):
        match = re.search(rf"(?im)^\s*{label}\s*:\s*(.+)$", chunk)
        if match:
            headers[label] = match.group(1).strip()
    return headers


def _has_complete_header_block(lines: list[str], start_index: int) -> bool:
    labels = set()
    for offset, line in enumerate(lines[start_index : start_index + 12]):
        stripped = line.strip().lower()
        if offset > 0 and stripped.startswith("from:"):
            return False
        if re.match(r"^from\s*:", stripped):
            labels.add("from")
        elif re.match(r"^(sent|date)\s*:", stripped):
            labels.add("sent")
        elif re.match(r"^to\s*:", stripped):
            labels.add("to")
        elif re.match(r"^subject\s*:", stripped):
            labels.add("subject")
        if {"from", "sent", "to", "subject"}.issubset(labels):
            return True
    return False


def _detect_sender_type(from_field: str) -> str:
    from_value = (from_field or "").lower()
    is_from_gng = any(pattern in from_value for pattern in GNG_PATTERNS)
    return "GNG" if is_from_gng else "Customer"


def _sender_label(sender_type: str) -> str:
    return "From GNG" if sender_type == "GNG" else "From Customer"


def _clean_name(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", value or "")
    cleaned = cleaned.replace('"', "").replace("'", "").strip()
    if "," in cleaned and len(cleaned.split(",")) == 2:
        last, first = [part.strip() for part in cleaned.split(",", 1)]
        cleaned = f"{first} {last}".strip()
    return cleaned


def _remove_label_prefix(chunk: str) -> str:
    text = re.sub(
        r"(?im)^\s*(?:\d+\.\s+)?(?:initial|follow-up|latest|agent)\s+email\s*:?\s*",
        "",
        chunk,
    )
    text = re.sub(r"(?im)^\s*on\s+.+\s+wrote:\s*", "", text)
    text = re.sub(r"(?im)^\s*[-]{2,}\s*original message\s*[-]{2,}\s*", "", text)
    return text.strip()


def _clean_email_body(body: str) -> str:
    lines = []
    for line in (body or "").splitlines():
        trimmed = line.strip()
        if any(pattern.search(trimmed) for pattern in IGNORED_BODY_LINE_PATTERNS):
            continue
        lines.append(line)
    return clean_text("\n".join(lines))


def _email_type(sender_type: str) -> str:
    return _sender_label(sender_type)
