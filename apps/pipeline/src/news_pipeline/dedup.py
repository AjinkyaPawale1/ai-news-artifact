"""Cross-source deduplication utilities."""

from __future__ import annotations

from .schema import Item


def deduplicate_items(items: list[Item]) -> list[Item]:
    """Deduplicate by exact URL for Day 1; fuzzy matching comes on Day 2."""
    seen: dict[str, Item] = {}
    for item in items:
        key = (item.url or item.title).strip().lower()
        if key and key not in seen:
            seen[key] = item
    return list(seen.values())
