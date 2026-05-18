from __future__ import annotations

import re
from typing import Any


ASK_NAME_RE = re.compile(r"\b(?:please\s+)?provide\s+the\s+name\s+on\s+the\s+account\b", re.I)
ASK_ADDRESS_RE = re.compile(r"\b(?:please\s+)?provide\s+the\s+(?:full\s+)?service\s+address\b", re.I)
ASK_ACCOUNT_RE = re.compile(r"\b(?:please\s+)?provide\s+the\s+account\s+number\b", re.I)
ADDRESS_RE = re.compile(
    r"\b\d{2,6}\s+[A-Za-z0-9 .'-]+(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|court|ct|circle|cir|trail|trl|way|place|pl|close)(?:\s+[A-Z]{2})?(?:,\s*[A-Za-z .'-]+)?(?:,\s*[A-Z]{2})?(?:\s+\d{5})?\b",
    re.I,
)
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")
ACCOUNT_NUMBER_RE = re.compile(r"\b\d{4,}(?:-\d{3,})+\b")
DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")


def sanitize_reply(reply: str) -> str:
    lines = []
    for line in (reply or "").splitlines():
        if re.search(r"\b(internal note|internal use|as an ai|ai-generated|draft note)\b", line, re.I):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def quality_check_reply(
    reply: str,
    emails: list[dict],
    account_data: dict[str, Any] | None = None,
    selected_category: str = "",
) -> dict[str, Any]:
    account_data = account_data or {}
    reply = reply or ""
    full_thread = _full_thread_text(emails)
    latest_customer = _latest_customer_email(emails)
    supplied_text = f"{full_thread}\n{_account_data_text(account_data)}"

    checks = [
        _check_answers_latest(reply, latest_customer, selected_category),
        _check_does_not_request_supplied_info(reply, emails, account_data),
        _check_no_unsupported_account_data(reply, supplied_text),
        _check_professional_tone(reply),
        _check_avoids_generic_uncertainty(reply, supplied_text),
        _check_gng_style_length(reply, selected_category),
        _check_avoids_unneeded_conditionals(reply),
        _check_next_steps(reply),
        _check_contact_language(reply),
    ]
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def _check_answers_latest(reply: str, latest_customer: dict | None, selected_category: str) -> dict[str, Any]:
    if not latest_customer:
        passed = bool(reply.strip())
    else:
        latest_text = latest_customer.get("body", "")
        required_terms = _category_terms(selected_category) or _important_terms(latest_text)
        passed = bool(reply.strip()) and (
            not required_terms
            or any(term in reply.lower() for term in required_terms)
            or "review" in reply.lower()
        )
    return _result("answers_latest_customer_email", passed, "Reply should address the latest customer message.")


def _check_does_not_request_supplied_info(
    reply: str,
    emails: list[dict],
    account_data: dict[str, Any],
) -> dict[str, Any]:
    text = _full_thread_text(emails)
    has_name = bool(account_data.get("customerName")) or bool(_find_customer_name(text)) or any(
        (email.get("senderType") == "Customer" or email.get("sender") == "Customer")
        and (email.get("fromName") or email.get("from"))
        and (email.get("fromName") or email.get("from")).lower() != "customer"
        for email in emails
    )
    has_address = bool(account_data.get("serviceAddress")) or bool(ADDRESS_RE.search(text))
    has_account = bool(account_data.get("accountNumber")) or bool(ACCOUNT_NUMBER_RE.search(text))

    issues = []
    if has_name and ASK_NAME_RE.search(reply):
        issues.append("asks for account name even though it is already provided")
    if has_address and ASK_ADDRESS_RE.search(reply):
        issues.append("asks for service address even though it is already provided")
    if has_account and ASK_ACCOUNT_RE.search(reply):
        issues.append("asks for account number even though it is already provided")

    return _result(
        "avoids_requesting_supplied_info",
        not issues,
        "; ".join(issues) or "Reply should not ask for information already provided.",
    )


def _check_no_unsupported_account_data(reply: str, supplied_text: str) -> dict[str, Any]:
    normalized_supply = _normalize(supplied_text)
    unsupported = []
    for pattern in (MONEY_RE, ACCOUNT_NUMBER_RE, DATE_RE):
        for value in pattern.findall(reply):
            if _normalize(value) not in normalized_supply:
                unsupported.append(value)
    unique_unsupported = sorted(set(unsupported))
    return _result(
        "avoids_unsupported_account_data",
        not unique_unsupported,
        f"Unsupported account values found: {', '.join(unique_unsupported)}"
        if unique_unsupported
        else "Reply should use only provided account values.",
    )


def _check_professional_tone(reply: str) -> dict[str, Any]:
    lower = reply.lower()
    issues = []
    if "as an ai" in lower or "ai-generated" in lower:
        issues.append("mentions AI")
    if "internal note" in lower or "internal use" in lower:
        issues.append("includes internal note language")
    if re.search(r"\b(hey|yo|whatever)\b", lower):
        issues.append("uses casual language")
    if reply.count("!") > 2:
        issues.append("uses too many exclamation points")
    return _result(
        "professional_tone",
        not issues,
        "; ".join(issues) or "Reply should stay professional and customer-ready.",
    )


def _check_avoids_generic_uncertainty(reply: str, supplied_text: str) -> dict[str, Any]:
    has_account_context = bool(
        ACCOUNT_NUMBER_RE.search(supplied_text)
        or _find_customer_name(supplied_text)
        or ADDRESS_RE.search(supplied_text)
    )
    lower = reply.lower()
    blocked = (
        "we do not have account details",
        "we do not have meter analysis results",
        "we do not have access",
        "we cannot confirm",
        "please provide verification",
    )
    found = [phrase for phrase in blocked if phrase in lower]
    passed = not (has_account_context and found)
    return _result(
        "avoids_generic_uncertainty",
        passed,
        f"Generic uncertainty language found despite account context: {', '.join(found)}"
        if found
        else "Reply should avoid generic uncertainty language when account context is present.",
    )


def _check_gng_style_length(reply: str, selected_category: str) -> dict[str, Any]:
    word_count = len(reply.split())
    paragraph_count = len([part for part in reply.split("\n\n") if part.strip()])
    minimum_words = 20 if selected_category == "Verification Needed" else 40
    minimum_paragraphs = 1 if selected_category == "Verification Needed" else 2
    passed = minimum_words <= word_count <= 500 and minimum_paragraphs <= paragraph_count <= 8
    return _result(
        "gng_style_length",
        passed,
        f"Reply has {word_count} words and {paragraph_count} paragraphs.",
    )


def _check_avoids_unneeded_conditionals(reply: str) -> dict[str, Any]:
    lower = reply.lower()
    blocked_phrases = (
        "if different from",
        "if applicable",
        "if needed",
        "once we have this information",
    )
    found = [phrase for phrase in blocked_phrases if phrase in lower]
    return _result(
        "avoids_unneeded_conditionals",
        not found,
        f"Unsupported conditional phrasing found: {', '.join(found)}"
        if found
        else "Reply should avoid unsupported conditional phrasing.",
    )


def _check_next_steps(reply: str) -> dict[str, Any]:
    lower = reply.lower()
    passed = any(
        phrase in lower
        for phrase in (
            "please",
            "once we receive",
            "next step",
            "let us know",
            "we can",
            "we will",
            "you can",
        )
    )
    return _result("correct_next_steps", passed, "Reply should include a clear next step.")


def _check_contact_language(reply: str) -> dict[str, Any]:
    lower = reply.lower()
    passed = any(
        phrase in lower
        for phrase in (
            "please let us know",
            "if you have any",
            "reply to this email",
            "customer care",
            "sincerely",
            "thank you",
        )
    )
    return _result(
        "contact_language",
        passed,
        "Reply should include polite closing/contact language when appropriate.",
    )


def _latest_customer_email(emails: list[dict]) -> dict | None:
    for email in reversed(emails or []):
        if email.get("senderType") == "Customer" or email.get("sender") == "Customer":
            return email
    return None


def _full_thread_text(emails: list[dict]) -> str:
    return "\n".join(
        " ".join(
            str(email.get(key, ""))
            for key in ("from", "fromName", "sender", "subject", "date", "timestamp", "body")
        )
        for email in emails or []
    )


def _account_data_text(account_data: dict[str, Any]) -> str:
    return "\n".join(str(value) for value in account_data.values() if value is not None)


def _find_customer_name(text: str) -> str:
    match = re.search(r"(?im)^\s*customer\s+name\s*:\s*(.+)$", text or "")
    return match.group(1).strip() if match else ""


def _category_terms(category: str) -> list[str]:
    return {
        "Billing Issue": ["bill", "billing", "balance", "charge", "charges"],
        "Payment Arrangement": ["payment", "arrangement", "balance", "eligibility"],
        "Move / Transfer Service": ["address", "service", "connection", "disconnection", "transfer"],
        "Name Change": ["name", "change"],
        "Meter Reading / High Usage": ["meter", "reading", "usage"],
        "Tenant / Responsibility Transfer": ["tenant", "service", "owner"],
        "Verification Needed": ["verify", "verification", "account", "address"],
    }.get(category, [])


def _important_terms(text: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z]{5,}\b", (text or "").lower())
    stop_words = {"please", "thank", "thanks", "would", "could", "about", "there", "their"}
    return [word for word in words if word not in stop_words][:8]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").lower())


def _result(name: str, passed: bool, message: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "message": message}
