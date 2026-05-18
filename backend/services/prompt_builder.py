import json
import re

from backend.services.category_prompts import MASTER_SYSTEM_PROMPT, get_category_prompt, normalize_category


SYSTEM_PROMPT = MASTER_SYSTEM_PROMPT


def build_user_payload(
    emails: list[dict],
    selected_category: str,
    agent_instructions: str,
    account_data: dict | None = None,
    previous_reply: str = "",
    regeneration_instruction: str = "",
) -> str:
    category = normalize_category(selected_category)
    account_data = account_data or {}
    account_context = _infer_account_context(emails, account_data, category)
    sections = [
        "CATEGORY:",
        get_category_prompt(category),
        "",
        "EMAIL THREAD:",
        _format_email_thread(emails),
        "",
        "ACCOUNT ACCESS CONTEXT:",
        _format_account_access_context(account_context),
        "",
        "VERIFICATION LOGIC:",
        _format_verification_logic(account_context),
        "",
        "ACCOUNT DATA:",
        _format_account_data(account_data),
        "",
        "AGENT INSTRUCTIONS:",
        agent_instructions.strip() or get_category_prompt(category),
    ]

    if previous_reply.strip():
        sections.extend(["", "PREVIOUS REPLY:", previous_reply.strip()])
    if regeneration_instruction.strip():
        sections.extend(["", "REGENERATION INSTRUCTION:", regeneration_instruction.strip()])

    sections.extend(
        [
            "",
            "QUALITY CHECK BEFORE RETURNING:",
            "- Does the reply answer the latest customer email?",
            "- Did it avoid asking for information already provided?",
            "- Did it avoid making up account data?",
            "- Is the tone formal, polished, customer-service oriented, and similar to Georgia Natural Gas correspondence?",
            "- Does it avoid sounding conversational, generic, or AI-generated?",
            "- Does it avoid unsupported conditional phrases such as 'if different from'?",
            "- For customer service requests, is it generally 2-4 professional paragraphs unless a shorter verification request is more appropriate?",
            "- Did it include standard customer support closing language when appropriate?",
            "- Does it include only correct next steps?",
            "",
            "TASK:",
            "Generate only the final customer-ready email response.",
        ]
    )
    return "\n".join(sections)


def _format_email_thread(emails: list[dict]) -> str:
    if not emails:
        return "No parsed emails were provided."

    lines = []
    for index, email in enumerate(emails, start=1):
        subject = email.get("subject") or "No subject"
        lines.extend(
            [
                f"{index}. {email.get('type', 'Email')}",
                f"Sender type: {email.get('senderType') or email.get('sender', '')}",
                f"From: {email.get('fromName') or email.get('sender', '')}",
                f"Date: {email.get('date') or email.get('timestamp', '')}",
                f"Subject: {subject}",
                "Body:",
                email.get("body", "").strip(),
                "",
            ]
        )
    return "\n".join(lines).strip()


def _format_account_data(account_data: dict) -> str:
    if not account_data:
        return (
            "No backend account data was provided. Do not invent balances, fees, dates, charges, credits, or policies.\n\n"
            "Expected account data fields later:\n"
            "- accountNumber\n"
            "- customerName\n"
            "- verified\n"
            "- balance\n"
            "- dueDate\n"
            "- previousBalance\n"
            "- currentGasCharges\n"
            "- budgetTrueUp\n"
            "- serviceAddress\n"
            "- meterAnalysis\n"
            "- eligibleForPaymentArrangement"
        )
    return json.dumps(account_data, ensure_ascii=False, indent=2)


def _format_account_access_context(context: dict) -> str:
    lines = [
        f"issueCategory: {context['issueCategory']}",
        f"accountVerified: {str(context['accountVerified']).lower()}",
        f"agentHasAccountAccess: {str(context['agentHasAccountAccess']).lower()}",
        f"needsVerification: {str(context['needsVerification']).lower()}",
        f"responseMode: {context['responseMode']}",
        f"accountNumberPresent: {str(context['accountNumberPresent']).lower()}",
        f"customerNamePresent: {str(context['customerNamePresent']).lower()}",
        f"serviceAddressPresent: {str(context['serviceAddressPresent']).lower()}",
        f"inquiryDetailsPresent: {str(context['inquiryDetailsPresent']).lower()}",
    ]

    if context["evidence"]:
        lines.append(f"accountContextEvidence: {', '.join(context['evidence'])}")

    if context["responseMode"] == "resolve_issue":
        lines.extend(
            [
                "Instruction: Do not ask for verification unless the email thread explicitly says verification is still required.",
                "Instruction: Generate the response as if the agent has reviewed the account internally.",
                "Instruction: Avoid generic uncertainty language such as 'we do not have account details' or 'we cannot confirm'.",
            ]
        )
    else:
        lines.append(f"recommendedVerificationRequest: {context['recommendedVerificationRequest']}")

    return "\n".join(lines)


def _format_verification_logic(context: dict) -> str:
    lines = [
        "Do not ask for information the customer already provided in the email thread or backend account data.",
    ]

    if context["responseMode"] == "resolve_issue":
        lines.extend(
            [
                "Account-identifying information is present. Treat the account as accessible to the agent.",
                "Do not request verification in the customer response.",
                "Respond directly to the customer issue using the selected category rules.",
            ]
        )
    else:
        lines.extend(
            [
                "Account-identifying information is missing or the category requires verification.",
                "Ask for missing verification only.",
                f"Recommended verification request: {context['recommendedVerificationRequest']}",
                "Use these exact request patterns when needed:",
                "- Missing name: Please provide the name on the account for further assistance.",
                "- Missing service address: Please provide the full service address for further assistance.",
                "- Missing account number: Please provide the account number or full service address.",
            ]
        )
    return "\n".join(lines)


def _infer_account_context(emails: list[dict], account_data: dict, category: str) -> dict:
    status = _verification_status(emails, account_data)
    inquiry_details_present = _has_inquiry_details(emails)
    account_verified = bool(
        account_data.get("verified") is True
        or status["has_account_number"]
        or (
            status["has_name"]
            and (status["has_service_address"] or inquiry_details_present)
        )
    )
    agent_has_access = bool(account_data) or status["has_account_number"] or account_verified
    needs_verification = not account_verified
    response_mode = "request_verification" if needs_verification else "resolve_issue"

    if category == "Verification Needed" and not account_verified:
        response_mode = "request_verification"
        needs_verification = True
    elif category != "Verification Needed" and agent_has_access:
        response_mode = "resolve_issue"
        needs_verification = False

    evidence = []
    if status["has_account_number"]:
        evidence.append("account number")
    if status["has_name"]:
        evidence.append("customer name")
    if status["has_service_address"]:
        evidence.append("service address")
    if inquiry_details_present:
        evidence.append("service inquiry details")
    if account_data.get("verified") is True:
        evidence.append("backend verified flag")

    return {
        "issueCategory": category,
        "accountVerified": account_verified,
        "agentHasAccountAccess": agent_has_access,
        "needsVerification": needs_verification,
        "responseMode": response_mode,
        "accountNumberPresent": status["has_account_number"],
        "customerNamePresent": status["has_name"],
        "serviceAddressPresent": status["has_service_address"],
        "inquiryDetailsPresent": inquiry_details_present,
        "recommendedVerificationRequest": "" if response_mode == "resolve_issue" else status["request"],
        "evidence": evidence,
    }


def _verification_status(emails: list[dict], account_data: dict) -> dict:
    if account_data.get("verified") is True:
        return {
            "verified": True,
            "request": "",
            "has_name": True,
            "has_service_address": True,
            "has_account_number": True,
        }

    full_text = " ".join(email.get("body", "") for email in emails)
    has_name = bool(account_data.get("customerName")) or bool(_find_customer_name(full_text)) or any(
        (email.get("senderType") == "Customer" or email.get("sender") == "Customer")
        and (email.get("fromName") or email.get("from"))
        and (email.get("fromName") or email.get("from")).lower() != "customer"
        for email in emails
    )
    has_service_address = bool(account_data.get("serviceAddress")) or bool(_find_service_address(full_text))
    has_account_number = bool(account_data.get("accountNumber")) or bool(_find_account_number(full_text))

    if not has_name:
        request = "Please provide the name on the account for further assistance."
    elif not has_service_address and not has_account_number:
        request = "Please provide the account number or full service address."
    elif not has_service_address:
        request = "Please provide the full service address for further assistance."
    else:
        request = ""

    return {
        "verified": False,
        "request": request,
        "has_name": has_name,
        "has_service_address": has_service_address,
        "has_account_number": has_account_number,
    }


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
