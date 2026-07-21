"""Normalization utilities for fetched items."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

from .dedup import canonicalize_url
from .schema import Item, SourceType, utc_now_iso

VALID_SOURCE_TYPES: set[SourceType] = {"paper", "github", "rss", "model", "tool_service"}


def _clean_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        normalized = " ".join(str(value).split())
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            cleaned.append(normalized)
    return cleaned


def _valid_http_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _normalize_related_links(values: list[str] | None, primary_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for value in _clean_list(values):
        canonical = canonicalize_url(value)
        if not _valid_http_url(canonical) or canonical == primary_url or canonical in seen:
            continue
        seen.add(canonical)
        links.append(canonical)
    return links


def _normalize_date(value: str, fallback: str) -> str:
    raw = (value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _valid_item(item: Item) -> bool:
    return bool(
        item.id.strip()
        and item.source.strip()
        and item.title.strip()
        and item.source_type in VALID_SOURCE_TYPES
        and _valid_http_url(item.url)
    )


def normalize_items(items: list[Item]) -> list[Item]:
    """Normalize shared fields and omit records that cannot satisfy the item contract."""
    normalized: list[Item] = []
    for item in items:
        item.id = " ".join((item.id or "").split())
        item.source = " ".join((item.source or "").split())
        item.title = " ".join((item.title or "").split())
        item.url = canonicalize_url(item.url)
        if not _valid_item(item):
            continue
        item.raw_content = " ".join((item.raw_content or "").split())[:2000]
        item.authors = _clean_list(item.authors) or ["Unknown"]
        item.tags = _clean_list(item.tags)
        primary_url = canonicalize_url(item.url)
        item.related_links = _normalize_related_links(item.related_links, primary_url)
        fetched_fallback = utc_now_iso()
        item.fetched_date = _normalize_date(item.fetched_date, fetched_fallback)
        item.published_date = _normalize_date(item.published_date, item.fetched_date)
        item.metadata = item.metadata if isinstance(item.metadata, dict) else {}
        normalized.append(item)
    return normalized
