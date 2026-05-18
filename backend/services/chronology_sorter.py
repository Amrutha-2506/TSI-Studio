def sort_chronologically(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            item.get("_sortTimestamp") is None,
            item.get("_sortTimestamp") or item.get("_originalIndex", 0),
            item.get("_originalIndex", 0),
        ),
    )
