"""RSS/blog extraction agent."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from html import unescape

import feedparser

from ..config import MAX_ITEMS_PER_SOURCE, RSS_FEEDS, window_start
from ..schema import Item, utc_now_iso

LOGGER = logging.getLogger(__name__)
HTML_TAG_RE = re.compile(r"<[^>]+>")
_LAST_DIAGNOSTICS: dict | None = None


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _strip_html(value: str) -> str:
    return " ".join(unescape(HTML_TAG_RE.sub(" ", value or "")).split())


def _entry_date(entry) -> str:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6]).isoformat()
    return getattr(entry, "published", "") or getattr(entry, "updated", "") or ""


def _entry_datetime(entry) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=window_start().tzinfo)
    return None


def _entry_content(entry) -> str:
    if getattr(entry, "content", None):
        first = entry.content[0]
        return _strip_html(first.get("value", ""))
    return _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))


def fetch_rss() -> list[Item]:
    """Fetch recent entries from configured RSS and Atom feeds."""
    global _LAST_DIAGNOSTICS  # noqa: PLW0603
    cutoff = window_start()
    feed_buckets: list[list[Item]] = []
    feed_diagnostics: list[dict] = []

    for feed_url in RSS_FEEDS:
        LOGGER.info("Fetching RSS feed %s", feed_url)
        feed = feedparser.parse(feed_url)
        source = feed.feed.get("title", feed_url) if getattr(feed, "feed", None) else feed_url
        entries = list(feed.entries[:MAX_ITEMS_PER_SOURCE])
        bucket: list[Item] = []

        for entry in entries:
            published_dt = _entry_datetime(entry)
            if published_dt and published_dt < cutoff:
                continue

            url = getattr(entry, "link", "") or feed_url
            title = getattr(entry, "title", "").strip()
            if not title:
                continue

            tags = [tag.get("term", "") for tag in getattr(entry, "tags", []) if tag.get("term")]
            bucket.append(
                Item(
                    id=f"rss-{_stable_id(url)}",
                    source=source,
                    source_type="rss",
                    title=title,
                    url=url,
                    authors=[getattr(entry, "author", "Unknown") or "Unknown"],
                    published_date=_entry_date(entry),
                    fetched_date=utc_now_iso(),
                    raw_content=_entry_content(entry),
                    tags=tags,
                )
            )

        feed_buckets.append(bucket)
        feed_diagnostics.append(
            {
                "feed_url": feed_url,
                "source": source,
                "fetched": len(entries),
                "eligible": len(bucket),
                "selected": 0,
            }
        )

    selected: list[Item] = []
    index = 0
    while len(selected) < MAX_ITEMS_PER_SOURCE:
        added = False
        for bucket_index, bucket in enumerate(feed_buckets):
            if index >= len(bucket):
                continue
            selected.append(bucket[index])
            feed_diagnostics[bucket_index]["selected"] += 1
            added = True
            if len(selected) >= MAX_ITEMS_PER_SOURCE:
                break
        if not added:
            break
        index += 1

    _LAST_DIAGNOSTICS = {
        "strategy": "round_robin",
        "feeds_requested": len(RSS_FEEDS),
        "selected": len(selected),
        "feeds": feed_diagnostics,
    }
    return selected


def get_last_diagnostics() -> dict | None:
    """Return diagnostics from the most recent RSS fetch."""
    return _LAST_DIAGNOSTICS


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in fetch_rss():
        print(item.to_dict())
