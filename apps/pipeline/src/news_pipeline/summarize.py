"""Summary generation placeholder for Day 4."""

from __future__ import annotations


def summarize_items(items: list[dict]) -> list[dict]:
    """Attach fallback summaries until LLM summarization is implemented."""
    for item in items:
        item["summary"] = item.get("summary") or (item.get("raw_content") or item.get("title", ""))[:240]
    return items
