def sort_chronologically(items: list[dict]) -> list[dict]:
    if len(items) > 1 and not any(item.get("_sortTimestamp") for item in items):
        return list(reversed(items))

    return sorted(
        items,
        key=lambda item: (
            item.get("_sortTimestamp") is None,
            item.get("_sortTimestamp") or item.get("_originalIndex", 0),
            item.get("_originalIndex", 0),
        ),
    )
