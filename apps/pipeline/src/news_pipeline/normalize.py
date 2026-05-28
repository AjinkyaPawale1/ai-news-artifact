"""Normalization utilities for fetched items."""

from __future__ import annotations

from .schema import Item


def normalize_items(items: list[Item]) -> list[Item]:
    """Return minimally normalized items for Day 1."""
    normalized: list[Item] = []
    for item in items:
        item.title = " ".join(item.title.split())
        item.raw_content = " ".join((item.raw_content or "").split())[:2000]
        item.authors = item.authors or ["Unknown"]
        item.published_date = item.published_date or item.fetched_date
        normalized.append(item)
    return normalized
