import re


def clean_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_email_headers(value: str) -> str:
    lines = []
    for line in value.splitlines():
        if re.match(r"^\s*(from|to|sent|date|subject|cc|bcc)\s*:", line, re.I):
            continue
        lines.append(line)
    return clean_text("\n".join(lines))
