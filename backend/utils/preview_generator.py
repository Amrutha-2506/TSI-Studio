from backend.utils.text_cleaner import clean_text


def make_preview(body: str, limit: int = 92) -> str:
    text = " ".join(clean_text(body).split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."
