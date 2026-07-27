"""Summary generation placeholder for Day 4."""

from __future__ import annotations

import re

MAX_SUMMARY_CHARS = 360


def _sentence_bounded_summary(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= MAX_SUMMARY_CHARS:
        return normalized
    truncated = normalized[:MAX_SUMMARY_CHARS]
    endings = list(re.finditer(r"[.!?](?:[\"')\]])?(?=\s|$)", truncated))
    if endings:
        return truncated[:endings[-1].end()].strip()
    return normalized


def summarize_items(items: list[dict]) -> list[dict]:
    """Attach fallback summaries until LLM summarization is implemented."""
    for item in items:
        item["summary"] = item.get("summary") or _sentence_bounded_summary(
            item.get("raw_content") or item.get("title", "")
        )
    return items
