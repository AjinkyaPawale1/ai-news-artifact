"""RSS/blog extraction agent."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser

import feedparser
import requests

from ..config import MAX_ITEMS_PER_SOURCE, RSS_FEEDS, window_start
from ..schema import Item, utc_now_iso

LOGGER = logging.getLogger(__name__)
HTML_TAG_RE = re.compile(r"<[^>]+>")
_LAST_DIAGNOSTICS: dict | None = None
REQUEST_HEADERS = {"User-Agent": "AI-Intelligence-Brief/1.0 (+https://github.com/AjinkyaPawale1/ai-news-artifact)"}
REQUEST_TIMEOUT_SECONDS = 12
MIN_SUMMARY_CHARS = 120
LINK_ACCESS_RESTRICTED_STATUS_CODES = {401, 403}
TUTORIAL_TITLE_TERMS = ("getting started", "how to", "tutorial", "guide", "profiling in", "part 1", "part 2", "part 3")
PROMOTIONAL_TITLE_TERMS = ("customer story", "customer stories", "case study", "how deutsche telekom", "teens deserve")
AI_SIGNAL_TERMS = (
    "ai",
    "artificial intelligence",
    "agent",
    "language model",
    "llm",
    "machine learning",
    "generative",
    "model",
    "inference",
    "retrieval",
    "rag",
    "pytorch",
    "vllm",
    "robotics",
    "multimodal",
    "foundation",
)
DECISION_SIGNAL_TERMS = (
    "release",
    "launch",
    "benchmark",
    "research",
    "developer",
    "deployment",
    "production",
    "open source",
    "dataset",
    "tool",
    "framework",
    "api",
    "inference",
    "evaluation",
)


class _MetadataParser(HTMLParser):
    """Extract an article description without adding an HTML parsing dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta" or self.description:
            return
        attributes = {name.lower(): value or "" for name, value in attrs}
        field = (attributes.get("name") or attributes.get("property") or "").lower()
        if field in {"description", "og:description", "twitter:description"}:
            self.description = _strip_html(attributes.get("content", ""))


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _strip_html(value: str) -> str:
    return " ".join(unescape(HTML_TAG_RE.sub(" ", value or "")).split())


def _entry_date(entry) -> str:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=window_start().tzinfo or timezone.utc).isoformat()
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


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def _summary_needs_enrichment(summary: str, title: str) -> bool:
    normalized_summary = _normalized_text(summary)
    if len(normalized_summary) < MIN_SUMMARY_CHARS or normalized_summary == _normalized_text(title):
        return True
    return not normalized_summary.rstrip().endswith((".", "!", "?"))


def _canonical_summary(url: str) -> tuple[str, str]:
    """Return a metadata description from a canonical article page when feed text is sparse."""
    try:
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
    except requests.RequestException:
        return "", "canonical_request_failed"

    if response.status_code >= 400:
        return "", f"canonical_http_{response.status_code}"

    parser = _MetadataParser()
    parser.feed(response.text[:250_000])
    summary = _strip_html(parser.description)
    if _summary_needs_enrichment(summary, ""):
        return "", "canonical_summary_too_short"
    return summary, ""


def _verify_link(url: str) -> tuple[bool, int]:
    """Verify rendered article links while tolerating bot-protected official sites."""
    try:
        response = requests.get(
            url,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
            stream=True,
        )
    except requests.RequestException:
        return False, 0

    status_code = response.status_code
    response.close()
    return status_code < 400 or status_code in LINK_ACCESS_RESTRICTED_STATUS_CODES, status_code


def _editorial_rejection(title: str, summary: str) -> str:
    title_text = _normalized_text(title)
    content = _normalized_text(f"{title} {summary}")
    if any(term in title_text for term in TUTORIAL_TITLE_TERMS):
        return "tutorial_or_onboarding"
    if any(term in title_text for term in PROMOTIONAL_TITLE_TERMS):
        return "customer_story_or_case_study"
    if not any(term in content for term in AI_SIGNAL_TERMS):
        return "missing_ai_signal"
    if not any(term in content for term in DECISION_SIGNAL_TERMS):
        return "missing_decision_signal"
    return ""


def fetch_rss() -> list[Item]:
    """Fetch recent entries from configured RSS and Atom feeds."""
    global _LAST_DIAGNOSTICS
    cutoff = window_start()
    feed_buckets: list[list[Item]] = []
    feed_diagnostics: list[dict] = []

    for feed_url in RSS_FEEDS:
        LOGGER.info("Fetching RSS feed %s", feed_url)
        feed = feedparser.parse(feed_url)
        source = feed.feed.get("title", feed_url) if getattr(feed, "feed", None) else feed_url
        entries = list(feed.entries[:MAX_ITEMS_PER_SOURCE])
        bucket: list[Item] = []
        rejected = Counter()
        verified = 0

        for entry in entries:
            published_dt = _entry_datetime(entry)
            if published_dt and published_dt < cutoff:
                continue

            url = getattr(entry, "link", "") or feed_url
            title = getattr(entry, "title", "").strip()
            if not title:
                rejected["missing_title"] += 1
                continue

            tags = [tag.get("term", "") for tag in getattr(entry, "tags", []) if tag.get("term")]
            content = _entry_content(entry)
            rejection = _editorial_rejection(title, content)
            if rejection:
                rejected[rejection] += 1
                continue
            if _summary_needs_enrichment(content, title):
                content, rejection = _canonical_summary(url)
                if rejection:
                    rejected[rejection] += 1
                    continue
            rejection = _editorial_rejection(title, content)
            if rejection:
                rejected[rejection] += 1
                continue
            link_verified, link_status = _verify_link(url)
            if not link_verified:
                rejected["link_verification_failed"] += 1
                continue
            verified += 1
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
                    raw_content=content,
                    tags=tags,
                    metadata={
                        "editorial_status": "eligible",
                        "link_verified": True,
                        "link_status": link_status,
                    },
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
                "verified": verified,
                "rejected": dict(sorted(rejected.items())),
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
