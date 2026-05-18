import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from backend.services.category_prompts import (
    METER_READING_HIGH_USAGE_TEMPLATE,
    STANDARD_CLOSING,
    get_category_prompt,
    normalize_category,
)
from backend.services.prompt_builder import SYSTEM_PROMPT, build_user_payload

BACKEND_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger(__name__)


def generate_reply(
    emails: list[dict],
    selected_category: str = "",
    agent_instructions: str = "",
    account_data: dict | None = None,
) -> str:
    return _generate_reply(
        emails,
        selected_category=selected_category,
        agent_instructions=agent_instructions,
        account_data=account_data or {},
        is_regeneration=False,
    )


def regenerate_reply(
    emails: list[dict],
    selected_category: str = "",
    agent_instructions: str = "",
    account_data: dict | None = None,
    previous_reply: str = "",
    regeneration_instruction: str = "",
) -> str:
    return _generate_reply(
        emails,
        selected_category=selected_category,
        agent_instructions=agent_instructions,
        account_data=account_data or {},
        previous_reply=previous_reply,
        regeneration_instruction=regeneration_instruction
        or "Generate a fresh variation while keeping the same facts, tone, and customer-service constraints.",
        is_regeneration=True,
    )


def _generate_reply(
    emails: list[dict],
    selected_category: str = "",
    agent_instructions: str = "",
    account_data: dict | None = None,
    previous_reply: str = "",
    regeneration_instruction: str = "",
    is_regeneration: bool = False,
) -> str:
    if not emails:
        raise ValueError("Cannot generate a reply without parsed emails.")

    category = normalize_category(selected_category)
    instructions = agent_instructions.strip() or get_category_prompt(category)
    account_data = account_data or {}

    if category == "Meter Reading / High Usage":
        logger.info("Using approved GNG meter/high-usage response template.")
        return METER_READING_HIGH_USAGE_TEMPLATE.format(
            customer_name=_customer_name(emails) or "Customer"
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key in {"your_openai_key_here", "your_key_here"}:
        logger.warning("OPENAI_API_KEY is missing; using fallback reply generation.")
        return _fallback_reply(emails, category, instructions, account_data, is_regeneration)

    try:
        from openai import OpenAI

        timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
        client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        logger.info(
            "OpenAI reply generation started: model=%s category=%s regeneration=%s email_count=%s",
            model,
            category,
            is_regeneration,
            len(emails),
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_payload(
                        emails,
                        category,
                        instructions,
                        account_data,
                        previous_reply,
                        regeneration_instruction,
                    ),
                },
            ],
            temperature=0.7 if is_regeneration else 0.35,
        )
        reply = response.choices[0].message.content.strip()
        logger.info(
            "OpenAI reply generation completed: model=%s category=%s regeneration=%s reply_chars=%s",
            model,
            category,
            is_regeneration,
            len(reply),
        )
        return reply
    except Exception as exc:
        logger.warning("OpenAI reply generation failed; using fallback reply. Error: %s", exc)
        return _fallback_reply(emails, category, instructions, account_data, is_regeneration)


def _fallback_reply(
    emails: list[dict],
    category: str,
    agent_instructions: str,
    account_data: dict,
    is_regeneration: bool = False,
) -> str:
    latest_customer = _latest_customer_email(emails) or emails[-1]
    salutation = _salutation(emails)
    details = _account_detail_lines(account_data)
    missing_request = _missing_verification_request(emails, account_data)
    intro = (
        "Thank you for following up with us."
        if is_regeneration
        else "Thank you for contacting Georgia Natural Gas."
    )

    if missing_request:
        return (
            f"{salutation}\n\n"
            f"{intro} We appreciate the opportunity to assist you. To help with your request, {missing_request}\n\n"
            "Please reply with this information so we may continue reviewing the account and provide the next steps. Please let us know if you have any additional questions or concerns.\n\n"
            f"{STANDARD_CLOSING}"
        )

    if category == "Billing Issue":
        body = _billing_body(details, latest_customer)
    elif category == "Payment Arrangement":
        body = _payment_body(details)
    elif category == "Move / Transfer Service":
        body = _move_body(latest_customer)
    elif category == "Name Change":
        effective_date = _find_effective_date(latest_customer.get("body", ""))
        body = (
            "We appreciate the opportunity to assist you with your name change request. "
            "Please provide us with the first and last name and the reason for the name change. "
        )
        if effective_date:
            body += f"We have noted the effective date provided in your message: {effective_date}. "
        else:
            body += "Please also provide the effective date for the requested name change. "
        body += "Please let us know if you have any additional questions or concerns. We hope you have a great day."
    elif category == "Meter Reading / High Usage":
        return METER_READING_HIGH_USAGE_TEMPLATE.format(
            customer_name=_customer_name(emails) or "Customer"
        )
    elif category == "Tenant / Responsibility Transfer":
        body = (
            "A tenant would need to apply for service in their own name. Once the tenant's service begins, the owner's service can be stopped "
            "or removed from the owner's name if requested."
        )
    else:
        preview = _compact(latest_customer.get("body", "your request"), 220)
        body = (
            f"We reviewed the latest message in the thread: \"{preview}\". "
            "We can continue reviewing the request using the information provided and will respond with confirmed next steps."
        )

    return (
        f"{salutation}\n\n"
        f"{_fallback_intro(category)} {body}\n\n"
        "Please let us know if you have any additional questions or concerns.\n\n"
        f"{STANDARD_CLOSING}"
    )


def _fallback_intro(category: str) -> str:
    if category == "Meter Reading / High Usage":
        return "Thank you for choosing Georgia Natural Gas."
    return "Thank you for contacting Georgia Natural Gas."


def _billing_body(details: list[str], latest_customer: dict) -> str:
    if details:
        return (
            "We reviewed the billing information available for the account. "
            + " ".join(details)
            + " These details explain the total based on the account data currently provided."
        )
    preview = _compact(latest_customer.get("body", "your billing question"), 180)
    return (
        f"We understand you are asking about the bill or charges mentioned in your latest message: \"{preview}\". "
        "At this time, no confirmed account balance or charge breakdown was provided to this tool, so we do not want to guess. "
        "Once the account details are available, we can explain the balance clearly."
    )


def _payment_body(details: list[str]) -> str:
    balance_line = next((line for line in details if "balance" in line.lower()), "")
    if balance_line:
        return (
            f"We can help review payment arrangement options. {balance_line} "
            "Please let us know when you would be able to make a payment, and we can review available options based on account eligibility."
        )
    return (
        "We can help review payment arrangement options once account access and eligibility are confirmed. "
        "We cannot promise approval until the account details confirm eligibility."
    )


def _move_body(latest_customer: dict) -> str:
    address = _find_service_address(latest_customer.get("body", ""))
    if address:
        return (
            f"We received the new service address: {address}. "
            "Please confirm the requested connection date and the disconnection date for the old address if those dates have not already been provided. "
            "A new account number may be created for the new service address."
        )
    return (
        "We can help with the move or transfer request. Please provide the new service address, requested connection date, "
        "and the disconnection date for the old address if those details have not already been provided."
    )


def _account_detail_lines(account_data: dict) -> list[str]:
    labels = {
        "balance": "Total balance",
        "dueDate": "Due date",
        "previousBalance": "Previous balance",
        "currentGasCharges": "Current gas charges",
        "budgetTrueUp": "Budget billing true-up",
        "meterAnalysis": "Meter analysis",
    }
    lines = []
    for key, label in labels.items():
        value = account_data.get(key)
        if value:
            lines.append(f"{label}: {value}.")
    return lines


def _missing_verification_request(emails: list[dict], account_data: dict) -> str:
    if account_data.get("verified") is True:
        return ""

    full_text = " ".join(email.get("body", "") for email in emails)
    has_name = bool(_customer_name(emails)) or bool(account_data.get("customerName")) or bool(_find_customer_name(full_text))
    has_address = bool(account_data.get("serviceAddress")) or bool(_find_service_address(full_text))
    has_account_number = bool(account_data.get("accountNumber")) or bool(_find_account_number(full_text))
    has_inquiry_details = _has_inquiry_details(emails)

    if has_account_number or (has_name and (has_address or has_inquiry_details)):
        return ""

    if not has_name:
        return "please provide the name on the account for further assistance."
    if not has_address and not has_account_number:
        return "please provide the account number or full service address for further assistance."
    if not has_address:
        return "please provide the full service address for further assistance."
    return ""


def _latest_customer_email(emails: list[dict]) -> dict | None:
    for email in reversed(emails):
        if email.get("senderType") == "Customer" or email.get("sender") == "Customer":
            return email
    return None


def _salutation(emails: list[dict]) -> str:
    name = _customer_name(emails)
    if not name:
        return "Dear Customer,"
    return f"Dear {name},"


def _customer_name(emails: list[dict]) -> str:
    for email in emails:
        body_name = _find_customer_name(email.get("body", ""))
        if body_name:
            return _format_customer_name(body_name)
        if email.get("senderType") == "Customer":
            name = (email.get("fromName") or "").strip()
            if name and name.lower() != "customer" and "@" not in name:
                return _format_customer_name(name)
    return ""


def _format_customer_name(name: str) -> str:
    cleaned = " ".join((name or "").split())
    if not cleaned:
        return ""
    if cleaned.isupper():
        return cleaned.title()
    return cleaned


def _find_customer_name(text: str) -> str:
    match = re.search(r"(?im)^\s*customer\s+name\s*:\s*(.+)$", text or "")
    return match.group(1).strip() if match else ""


def _find_account_number(text: str) -> str:
    match = re.search(r"(?im)^\s*account\s+number\s*:\s*([A-Za-z0-9-]+)", text or "")
    if match:
        return match.group(1).strip()
    generic = re.search(r"\b\d{4,}(?:-\d{3,})?\b", text or "")
    return generic.group(0).strip() if generic else ""


def _has_inquiry_details(emails: list[dict]) -> bool:
    full_text = " ".join(
        " ".join(str(email.get(key, "")) for key in ("subject", "body"))
        for email in emails or []
    ).lower()
    return any(
        marker in full_text
        for marker in (
            "message:",
            "topic:",
            "requesting",
            "meter",
            "usage",
            "billing",
            "payment",
            "transfer",
            "move",
            "name change",
        )
    )


def _find_service_address(text: str) -> str:
    match = re.search(
        r"\b\d{2,6}\s+[A-Za-z0-9 .'-]+(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln|court|ct|circle|cir|trail|trl|way|place|pl|close)(?:\s+[A-Z]{2})?(?:,\s*[A-Za-z .'-]+)?(?:,\s*[A-Z]{2})?(?:\s+\d{5})?\b",
        text,
        re.I,
    )
    return match.group(0).strip() if match else ""


def _find_effective_date(text: str) -> str:
    match = re.search(
        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{1,2},?\s+\d{4}\b"
        r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        text or "",
        re.I,
    )
    return match.group(0).strip() if match else ""


def _compact(text: str, limit: int) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."
