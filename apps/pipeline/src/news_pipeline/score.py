"""Relevance scoring utilities."""

from __future__ import annotations

from .config import AI_KEYWORDS, DOMAIN_KEYWORDS
from .schema import Item


def _count_matches(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lower)


def score_items(items: list[Item]) -> list[dict]:
    """Attach a simple Day 1 score to each item."""
    scored: list[dict] = []
    for item in items:
        text = f"{item.title} {item.raw_content} {' '.join(item.tags)}"
        domain = min(_count_matches(text, DOMAIN_KEYWORDS) * 2, 10)
        ai = min(_count_matches(text, AI_KEYWORDS) * 2, 10)
        score = max(40, int((domain * 0.4 + ai * 0.6) * 10))
        record = item.to_dict()
        record["score"] = min(score, 100)
        scored.append(record)
    return sorted(scored, key=lambda item: item["score"], reverse=True)
