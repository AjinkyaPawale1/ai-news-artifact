"""Shared schema for pipeline items."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

SourceType = Literal["paper", "github", "rss", "model", "tool_service"]


def utc_now_iso() -> str:
    """Return the current UTC timestamp as ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Item:
    """Unified item produced by every fetch agent."""

    id: str
    source: str
    source_type: SourceType
    title: str
    url: str
    authors: list[str] = field(default_factory=list)
    published_date: str = ""
    fetched_date: str = field(default_factory=utc_now_iso)
    raw_content: str = ""
    tags: list[str] = field(default_factory=list)
    related_links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the item to a JSON-serializable dict."""
        return asdict(self)
