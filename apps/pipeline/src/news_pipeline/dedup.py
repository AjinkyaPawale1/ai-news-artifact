"""Cross-source deduplication utilities."""

from __future__ import annotations

from .schema import Item

SPECIFIC_RELEASE_TYPES = {"model", "tool_service"}


def deduplicate_items(items: list[Item]) -> list[Item]:
    """Deduplicate by exact URL for Day 1; fuzzy matching comes on Day 2."""
    seen: dict[str, Item] = {}
    for item in items:
        key = (item.url or item.title).strip().lower()
        if not key:
            continue
        existing = seen.get(key)
        if not existing:
            seen[key] = item
            continue
        if existing.source_type == "rss" and item.source_type in SPECIFIC_RELEASE_TYPES:
            seen[key] = item
    return list(seen.values())
