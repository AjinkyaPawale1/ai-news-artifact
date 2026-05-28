"""Quality gate for scored items."""

from __future__ import annotations


def apply_quality_gate(items: list[dict], threshold: int = 40) -> list[dict]:
    """Pass items that meet the Day 1 minimum score threshold."""
    return [item for item in items if item.get("score", 0) >= threshold]
