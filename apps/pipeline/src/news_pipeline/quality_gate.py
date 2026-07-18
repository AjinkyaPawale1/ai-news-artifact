"""Quality gate for scored items."""

from __future__ import annotations


def apply_quality_gate(items: list[dict], threshold: int = 40) -> list[dict]:
    """Keep source-specific candidates that meet the shared publication minimum."""
    passed: list[dict] = []
    for item in items:
        if item.get("score", 0) < threshold:
            continue
        if item.get("source_type") == "rss":
            metadata = item.get("metadata") or {}
            if metadata.get("editorial_status") != "eligible" or not metadata.get("link_verified"):
                continue
        passed.append(item)
    return passed
