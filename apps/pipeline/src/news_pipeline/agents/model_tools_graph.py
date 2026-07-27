"""LangGraph workflow for model release and AI tool/service extraction."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, Literal, TypedDict
from urllib.parse import urljoin

import feedparser
import requests

from ..config import DATE_WINDOW_DAYS, window_start
from ..model_tools_config import (
    MODEL_TOOL_CORE_FEEDS,
    MODEL_TOOL_CORE_MODEL_TERMS,
    MODEL_TOOL_CORE_TOOL_SERVICE_TERMS,
    MODEL_TOOL_FEED_SCAN_LIMIT,
    MODEL_TOOL_HOSTING_RELEASE_TERMS,
    MODEL_TOOL_LLM_CLASSIFY,
    MODEL_TOOL_LLM_CLASSIFY_LIMIT,
    MODEL_TOOL_MAJOR_MODEL_WINDOW_DAYS,
    MODEL_TOOL_MAX_ITEMS,
    MODEL_TOOL_MODEL_UPDATE_ONLY_TERMS,
    MODEL_TOOL_RELEASE_TERMS,
    MODEL_TOOL_SOURCE_PAGES,
)
from ..schema import Item, utc_now_iso
from .model_tools_dynamic import resolve_dynamic_model_tool_inputs

LOGGER = logging.getLogger(__name__)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
MONTH_DATE_RE = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+20\d{2}\b",
    flags=re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?:[T ][0-2]\d:\d{2}:\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?\b")
URL_DATE_RE = re.compile(r"/(20\d{2})/(\d{2})/(\d{2})(?:/|$)")
MARKDOWN_UPDATE_RE = re.compile(
    r'<Update\s+label="([^"]+)"[^>]*>(.*?)</Update>',
    flags=re.DOTALL,
)
MARKDOWN_HEADING_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$", flags=re.MULTILINE)
PRODUCT_VERSION_RE = re.compile(r"\bv?\d+(?:\.\d+)*\b", flags=re.IGNORECASE)
PRODUCT_AVAILABILITY_RE = re.compile(
    r":\s*(?:now\s+)?(?:available|released|preview|beta)\b",
    flags=re.IGNORECASE,
)
MAJOR_MODEL_FAMILY_RE = re.compile(
    r"\b(?:gpt|claude|gemini|llama|mistral|mixtral|command|grok|deepseek|qwen|phi|gemma|o[134])"
    r"(?:[-\s]?[a-z]+){0,2}[-\s]?\d+(?:\.\d+)*\b",
    flags=re.IGNORECASE,
)
MAJOR_MODEL_VARIANT_RE = re.compile(
    r"^[-\s]+(?:sol|terra|luna|pro|flash|ultra|mini|nano|opus|sonnet|haiku)\b",
    flags=re.IGNORECASE,
)
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
_LAST_DIAGNOSTICS: dict[str, Any] | None = None
_OPENAI_CLASSIFY_ATTEMPTS = 0
_OPENAI_CLASSIFY_FAILURES = 0
_OPENAI_CLASSIFY_DISABLED_FOR_RUN = False

ReleaseKind = Literal["model", "tool_service"]


class ModelToolsState(TypedDict, total=False):
    feeds: list[str]
    source_pages: list[str]
    model_terms: list[str]
    tool_terms: list[str]
    dynamic_config: dict[str, Any]
    entries: list[dict[str, Any]]
    classified: list[dict[str, Any]]
    selected: list[dict[str, Any]]
    items: list[Item]
    classification_diagnostics: dict[str, int]
    selection_diagnostics: dict[str, int]


ORG_HINTS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "hugging face": "Hugging Face",
    "google": "Google",
    "microsoft": "Microsoft",
    "meta": "Meta",
    "mistral": "Mistral AI",
    "cohere": "Cohere",
    "nvidia": "NVIDIA",
    "aws": "AWS",
    "github": "GitHub",
    "perplexity": "Perplexity",
    "elevenlabs": "ElevenLabs",
}
NON_RELEASE_HEADLINE_TERMS = [
    "how ",
    "how to ",
    "guide",
    "tutorial",
    "case study",
    "customer story",
    "best practices",
    "accelerate ",
    "enable ",
    "training ",
    "using ",
    "build ",
    "building ",
]
CONSUMER_HEADLINE_TERMS = [
    "for teachers",
    "for educators",
    "for students",
    "in chrome",
    "waze",
]
TITLE_AVAILABILITY_TERMS = [
    "now supports",
    "now available",
    "on amazon bedrock",
    "on sagemaker",
]
NON_PRODUCT_ANNOUNCEMENT_TERMS = [
    "acquires ",
    "acquisition",
    "appoints ",
    "collaboration",
    "expands presence",
    "expansion",
    "funding",
    "joins forces",
    "opens office",
    "partners with",
    "partnership",
]
SOURCE_PAGE_PRODUCT_TERMS = [
    "api",
    "cli",
    "dubbing",
    "integration",
    "model",
    "music",
    "platform",
    "sdk",
    "search",
    "tool",
    "ui",
]
MAJOR_MODEL_ORGS = {
    "Anthropic",
    "Cohere",
    "Google",
    "Meta",
    "Mistral AI",
    "OpenAI",
}
MAJOR_MODEL_IMPACT_TERMS = [
    "flagship",
    "frontier",
    "generally available",
    "available to all",
    "available to everyone",
    "available in chatgpt",
    "available via the api",
    "model family",
    "next-generation model",
]
MAJOR_MODEL_BROAD_REACH_TERMS = [
    "api",
    "business",
    "chatgpt",
    "consumer",
    "developers",
    "enterprise",
    "production",
    "public",
    "users",
]


class LinkParser(HTMLParser):
    """Small HTML collector for official source pages without RSS."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.meta_descriptions: list[str] = []
        self.paragraphs: list[str] = []
        self.title = ""
        self._href = ""
        self._text: list[str] = []
        self._in_title = False
        self._in_paragraph = False
        self._paragraph_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            content = attrs_dict.get("content") or ""
            if name in {"description", "og:description", "twitter:description"} and content:
                self.meta_descriptions.append(" ".join(content.split()))
        if tag == "p":
            self._in_paragraph = True
            self._paragraph_text = []
        if tag == "a":
            self._href = attrs_dict.get("href") or ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_paragraph:
            self._paragraph_text.append(data)
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "p":
            text = " ".join(" ".join(self._paragraph_text).split())
            if len(text) > 40:
                self.paragraphs.append(text)
            self._in_paragraph = False
            self._paragraph_text = []
        if tag == "a" and self._href:
            text = " ".join(" ".join(self._text).split())
            if text:
                self.links.append((self._href, text))
            self._href = ""
            self._text = []


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _strip_html(value: str) -> str:
    return WHITESPACE_RE.sub(" ", unescape(HTML_TAG_RE.sub(" ", value or ""))).strip()


def _entry_date(entry) -> str:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=window_start().tzinfo).isoformat()
    return getattr(entry, "published", "") or getattr(entry, "updated", "") or ""


def _entry_datetime(entry) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        return datetime(*parsed[:6], tzinfo=window_start().tzinfo)
    return None


def _entry_content(entry) -> str:
    if getattr(entry, "content", None):
        return _strip_html(entry.content[0].get("value", ""))
    return _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))


def _source_name(url: str) -> str:
    host = re.sub(r"^www\.", "", url.split("//", 1)[-1].split("/", 1)[0])
    if "openai" in host:
        return "OpenAI"
    if "anthropic" in host:
        return "Anthropic"
    if "huggingface" in host:
        return "Hugging Face"
    if "mistral" in host:
        return "Mistral AI"
    if "cohere" in host:
        return "Cohere"
    if "meta" in host:
        return "Meta"
    if "microsoft" in host or "azure" in host:
        return "Microsoft"
    if "nvidia" in host:
        return "NVIDIA"
    if "amazon" in host or "aws" in host:
        return "AWS"
    if "github" in host:
        return "GitHub"
    if "perplexity" in host:
        return "Perplexity"
    if "elevenlabs" in host:
        return "ElevenLabs"
    if "google" in host:
        return "Google"
    return host or url


def _date_from_text(value: str) -> str:
    match = MONTH_DATE_RE.search(value or "")
    if match:
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(match.group(0).replace(".", ""), fmt).replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                continue

    iso_match = ISO_DATE_RE.search(value or "")
    if iso_match:
        parsed = _parse_datetime_value(iso_match.group(0))
        if parsed:
            return parsed.isoformat()

    return ""


def _parse_datetime_value(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None

    normalized = raw.replace("Z", "+00:00")
    for candidate in (normalized, normalized.replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw.replace(".", ""), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def _date_from_url(url: str) -> str:
    match = URL_DATE_RE.search(url or "")
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}T00:00:00+00:00"


def _published_date_from_html(html: str, headers: Any) -> str:
    candidates = [
        r'(?:property|name|itemprop)="(?:article:published_time|og:published_time|publishdate|pubdate|datePublished|dateModified)"[^>]*content="([^"]+)"',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"dateModified"\s*:\s*"([^"]+)"',
        r'<time[^>]*datetime="([^"]+)"',
    ]
    for pattern in candidates:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            parsed = _parse_datetime_value(match.group(1))
            if parsed:
                return parsed.isoformat()

    text_match = _date_from_text(_strip_html(html)[:6000])
    if text_match:
        return text_match

    last_modified = headers.get("Last-Modified") if headers else ""
    parsed = _parse_datetime_value(last_modified)
    return parsed.isoformat() if parsed else ""


def _link_is_relevant(source_page: str, url: str, title: str) -> bool:
    if "#" in url or len(title) < 8:
        return False
    title_lower = title.lower()
    if title_lower in {"news", "research", "blog", "products", "learn more", "read all news"}:
        return False
    source_host = source_page.split("//", 1)[-1].split("/", 1)[0].replace("www.", "")
    url_host = url.split("//", 1)[-1].split("/", 1)[0].replace("www.", "")
    if source_host and url_host and source_host not in url_host and url_host not in source_host:
        return False
    if "ai.google.dev" in source_host and "/docs/" in url:
        return "whats-new" in url or "changelog" in url
    if "cohere.com" in source_host and url.rstrip("/") == "https://cohere.com/research":
        return False
    if "research lab" in title_lower and "model" not in title_lower:
        return False
    return any(part in url for part in ("/news", "/engineering", "/blog", "/research", "/docs", "/gemini"))


def _markdown_text(value: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    text = re.sub(r"[`*_#>-]+", " ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _month_end_date(label: str) -> str:
    try:
        month = datetime.strptime(label.strip(), "%B %Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    last_day = monthrange(month.year, month.month)[1]
    resolved = month.replace(day=last_day, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if (month.year, month.month) >= (now.year, now.month):
        return ""
    return resolved.isoformat()


def _fetch_markdown_changelog_entries(page_url: str, markdown: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    source = _source_name(page_url)
    canonical_url = page_url.removesuffix(".md")
    ignored_headings = {"Highlights:", "Key capabilities:", "What this means:"}

    for update_match in MARKDOWN_UPDATE_RE.finditer(markdown):
        label, block = update_match.groups()
        published_date = _month_end_date(label)
        if not published_date:
            continue
        headings = list(MARKDOWN_HEADING_RE.finditer(block))
        for index, heading in enumerate(headings):
            title = _markdown_text(heading.group(1))
            if title in ignored_headings or len(title) < 8:
                continue
            content_end = headings[index + 1].start() if index + 1 < len(headings) else len(block)
            content = _markdown_text(block[heading.end() : content_end])[:1800]
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]
            entries.append(
                {
                    "source": source,
                    "title": title,
                    "url": f"{canonical_url}#{label.lower().replace(' ', '-')}-{slug}",
                    "published_date": published_date,
                    "content": content or title,
                    "source_page": True,
                    "source_url": page_url,
                    "source_label": "Source page",
                }
            )
    return entries


def _article_metadata(url: str, title: str) -> dict[str, str]:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.debug("Article excerpt fetch failed for %s: %s", url, exc)
        return {"excerpt": "", "published_date": _date_from_url(url)}

    parser = LinkParser()
    parser.feed(response.text[:500000])
    title_terms = [term for term in re.split(r"[^a-z0-9]+", title.lower()) if len(term) > 3]
    signal_terms = ["announc", "introduc", "release", "available", "model", "agent", "api", "sdk", "tool"]
    generic_terms = ["the most powerful ai platform", "build, test, and run", "train, align, and evaluate"]
    focused = []
    for paragraph in parser.paragraphs:
        lower = paragraph.lower()
        if any(term in lower for term in generic_terms):
            continue
        matches_title_terms = bool(title_terms) and any(term in lower for term in title_terms[:5])
        matches_signal_terms = (not title_terms) and any(term in lower for term in signal_terms)
        if matches_title_terms or matches_signal_terms:
            focused.append(paragraph)
    parts = [*focused[:4], *parser.meta_descriptions[:1]]
    published_date = _published_date_from_html(response.text[:500000], response.headers) or _date_from_url(url)
    return {
        "excerpt": " ".join(parts)[:1800].strip(),
        "published_date": published_date,
    }


def _resolve_entry_date(entry: dict[str, Any], cutoff: datetime) -> dict[str, Any] | None:
    parsed = _parse_datetime_value(entry.get("published_date", ""))
    if parsed:
        if parsed < cutoff:
            return None
        return {**entry, "published_date": parsed.isoformat()}

    metadata = _article_metadata(entry.get("url", ""), entry.get("title", ""))
    resolved = _parse_datetime_value(metadata.get("published_date", ""))
    if not resolved or resolved < cutoff:
        return None

    content = metadata.get("excerpt") or entry.get("content", "")
    return {
        **entry,
        "published_date": resolved.isoformat(),
        "content": content,
    }


def _fetch_source_page_entries(source_pages: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for page_url in source_pages:
        try:
            response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Source page fetch failed for %s: %s", page_url, exc)
            continue

        if page_url.endswith(".md") or "markdown" in response.headers.get("Content-Type", ""):
            entries.extend(_fetch_markdown_changelog_entries(page_url, response.text))
            continue

        parser = LinkParser()
        parser.feed(response.text[:500000])
        source = _source_name(page_url)
        page_title = " ".join((parser.title or page_url).split())
        page_content = _strip_html(response.text)[:4000]
        if "ai.google.dev" not in page_url and any(term in page_url.lower() for term in ("changelog", "release-notes", "releases")):
            entries.append(
                {
                    "source": source,
                    "title": page_title,
                    "url": page_url,
                    "published_date": "",
                    "content": page_content,
                    "source_page": True,
                    "source_url": page_url,
                    "source_label": "Source page",
                }
            )

        seen: set[str] = {page_url}
        for href, title in parser.links[:80]:
            url = urljoin(page_url, href)
            if url in seen or not _link_is_relevant(page_url, url, title):
                continue
            seen.add(url)
            entries.append(
                {
                    "source": source,
                    "title": title,
                    "url": url,
                    "published_date": _date_from_text(title),
                    "content": title,
                    "source_page": True,
                    "source_url": page_url,
                    "source_label": "Source page",
                }
            )
    return entries


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(_term_in_text(text, term) for term in terms)


def _term_count(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if _term_in_text(text, term))


def _term_in_text(text: str, term: str) -> bool:
    if not term:
        return False
    if not term.replace("-", "").replace(" ", "").isalnum():
        return term in text
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _major_model_cutoff(standard_cutoff: datetime) -> datetime:
    extension_days = max(0, MODEL_TOOL_MAJOR_MODEL_WINDOW_DAYS - DATE_WINDOW_DAYS)
    return standard_cutoff - timedelta(days=extension_days)


def _major_model_family(title: str) -> str:
    match = MAJOR_MODEL_FAMILY_RE.search(title or "")
    if not match:
        return ""
    return re.sub(r"[^a-z0-9]+", "", match.group(0).lower())


def _major_model_name(title: str) -> str:
    match = MAJOR_MODEL_FAMILY_RE.search(title or "")
    if not match:
        return ""
    name = match.group(0)
    variant = MAJOR_MODEL_VARIANT_RE.match(title[match.end() :])
    if variant and variant.group(0).strip(" -").casefold() not in name.casefold().split():
        name += variant.group(0)
    return " ".join(name.split()).strip(" -:|")


def _major_model_impact(entry: dict[str, Any], org: str) -> tuple[str, int]:
    title = entry.get("title", "")
    text = f"{title} {entry.get('content', '')}".lower()
    family = _major_model_family(title)
    if org not in MAJOR_MODEL_ORGS or not family:
        return "", 0

    title_text = title.lower()
    impact_hits = _term_count(text, MAJOR_MODEL_IMPACT_TERMS)
    broad_reach_hits = _term_count(text, MAJOR_MODEL_BROAD_REACH_TERMS)
    headline_impact = _contains_any(title_text, MAJOR_MODEL_IMPACT_TERMS)
    headline_release = _contains_any(title_text, [*MODEL_TOOL_RELEASE_TERMS, *TITLE_AVAILABILITY_TERMS])
    if not headline_impact and not headline_release:
        return "", 0
    if not impact_hits and not broad_reach_hits:
        return "", 0

    score = 60 + min(25, impact_hits * 10) + min(15, broad_reach_hits * 3)
    if _contains_any(title_text, ["flagship", "frontier"]):
        score += 10
    if _contains_any(title_text, ["preview", "previewing"]):
        score -= 15
    return family, min(100, score)


def _org_from_source(source: str, text: str) -> str:
    known_sources = {
        "OpenAI",
        "Anthropic",
        "Hugging Face",
        "Google",
        "Microsoft",
        "Meta",
        "Mistral AI",
        "Cohere",
        "NVIDIA",
        "AWS",
        "GitHub",
        "Perplexity",
        "ElevenLabs",
    }
    if source in known_sources:
        return source
    haystack = f"{source} {text}".lower()
    for key, org in ORG_HINTS.items():
        if key in haystack:
            return org
    return source.split("|")[0].replace("News", "").strip() or "AI"


def _clean_name(title: str) -> str:
    name = re.sub(
        r"^(announcing|introducing|introduce|launching|launch|released?|new)\s+",
        "",
        title.strip(),
        flags=re.IGNORECASE,
    )
    name = re.split(r"\s*(?::|\|)\s+|\s+-\s+", name, maxsplit=1)[0].strip()
    return name or title.strip()


def _model_tag(text: str) -> str:
    if _contains_any(text, ["open weights", "open-weight", "open source", "open-source"]):
        return "OPEN"
    if _term_in_text(text, "embedding"):
        return "EMBED"
    if _contains_any(text, ["api", "available", "generally available", "ga"]):
        return "API"
    return "MODEL"


def _tool_tag(text: str) -> str:
    if _contains_any(text, ["terminal", "cli", "command line"]):
        return "CLI"
    if _contains_any(text, ["ide", "vs code", "copilot", "cursor"]):
        return "IDE"
    if _contains_any(text, ["cloud", "service", "hosted", "azure"]):
        return "CLOUD"
    if _term_in_text(text, "sdk"):
        return "SDK"
    if _term_in_text(text, "api"):
        return "API"
    return "PLATFORM"


def _note(title: str, content: str) -> str:
    text = content or title
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    note = " ".join(sentence for sentence in sentences[:2] if sentence).strip()
    return (note or title)[:260].rstrip()


def _release_score(text: str, kind: ReleaseKind) -> int:
    release_score = _term_count(text, MODEL_TOOL_RELEASE_TERMS) * 3
    focus_terms = MODEL_TOOL_CORE_MODEL_TERMS if kind == "model" else MODEL_TOOL_CORE_TOOL_SERVICE_TERMS
    focus_score = _term_count(text, focus_terms) * 4
    return release_score + focus_score


def _has_hosting_release_signal(text: str) -> bool:
    return _contains_any(text, MODEL_TOOL_HOSTING_RELEASE_TERMS)


def _is_model_update_only(title_text: str) -> bool:
    return _contains_any(title_text, MODEL_TOOL_MODEL_UPDATE_ONLY_TERMS)


def _source_page_title_has_product_signal(
    title_text: str,
    *,
    title_model_score: int,
    title_tool_score: int,
) -> bool:
    if any(term in title_text for term in NON_PRODUCT_ANNOUNCEMENT_TERMS):
        return False
    return bool(
        title_model_score
        or title_tool_score
        or _contains_any(title_text, SOURCE_PAGE_PRODUCT_TERMS)
        or PRODUCT_VERSION_RE.search(title_text)
        or PRODUCT_AVAILABILITY_RE.search(title_text)
    )


def _classify_entry(
    entry: dict[str, Any],
    *,
    model_terms: list[str],
    tool_terms: list[str],
) -> dict[str, Any] | None:
    title = entry["title"]
    content = entry["content"]
    title_text = title.lower()
    text = f"{title} {content}".lower()
    title_model_score = _term_count(title_text, model_terms)
    title_tool_score = _term_count(title_text, tool_terms)
    title_has_release_signal = _contains_any(title_text, MODEL_TOOL_RELEASE_TERMS)
    title_has_availability_signal = _contains_any(title_text, TITLE_AVAILABILITY_TERMS)
    org = _org_from_source(entry["source"], text)
    major_model_family, impact_score = _major_model_impact(entry, org)
    major_release = bool(major_model_family)
    if _contains_any(title_text, CONSUMER_HEADLINE_TERMS):
        return None
    if entry.get("source_page") and not _source_page_title_has_product_signal(
        title_text,
        title_model_score=title_model_score,
        title_tool_score=title_tool_score,
    ):
        return None
    if title_model_score == 0 and title_tool_score == 0:
        content_has_focus = _contains_any(text, model_terms) or _contains_any(text, tool_terms)
        if not entry.get("source_page") or not title_has_release_signal or not content_has_focus:
            return None

    has_release_signal = title_has_release_signal or title_has_availability_signal or major_release
    looks_like_non_release_article = any(term in title_text for term in NON_RELEASE_HEADLINE_TERMS)
    if looks_like_non_release_article and not title_has_release_signal:
        return None
    if not has_release_signal:
        return None
    if _is_model_update_only(title_text):
        return None

    release_score = _term_count(text, MODEL_TOOL_RELEASE_TERMS) * 3
    model_score = release_score + _term_count(text, model_terms) * 4 + title_model_score * 8
    tool_score = release_score + _term_count(text, tool_terms) * 4 + title_tool_score * 8
    if model_score < 7 and tool_score < 7:
        return None

    kind: ReleaseKind = "model" if model_score >= tool_score else "tool_service"
    if major_release:
        kind = "model"
    if kind == "model" and _has_hosting_release_signal(title_text):
        kind = "tool_service"
        major_release = False
        major_model_family = ""
        impact_score = 0
    return {
        **entry,
        "kind": kind,
        "name": _major_model_name(title) if major_release else _clean_name(title),
        "org": org,
        "note": _note(title, content),
        "tag": _model_tag(text) if kind == "model" else _tool_tag(text),
        "release_score": max(model_score, tool_score),
        "major_release": major_release,
        "major_model_family": major_model_family,
        "impact_score": impact_score,
        "classifier": "deterministic",
    }


def _normalize_llm_tag(kind: str, value: str) -> str:
    tag = " ".join(str(value or "").upper().split())[:12]
    allowed = {"API", "OPEN", "EMBED", "MODEL"} if kind == "model" else {
        "CLI",
        "IDE",
        "CLOUD",
        "SDK",
        "API",
        "PLATFORM",
    }
    return tag if tag in allowed else ("MODEL" if kind == "model" else "PLATFORM")


def _openai_classify_entry(
    entry: dict[str, Any],
    deterministic: dict[str, Any],
    *,
    llm_available: bool,
) -> dict[str, Any] | None:
    global _OPENAI_CLASSIFY_ATTEMPTS, _OPENAI_CLASSIFY_FAILURES, _OPENAI_CLASSIFY_DISABLED_FOR_RUN
    api_key = os.getenv("OPENAI_API_KEY")
    if (
        not api_key
        or not llm_available
        or not MODEL_TOOL_LLM_CLASSIFY
        or _OPENAI_CLASSIFY_DISABLED_FOR_RUN
        or _OPENAI_CLASSIFY_ATTEMPTS >= MODEL_TOOL_LLM_CLASSIFY_LIMIT
    ):
        return deterministic
    _OPENAI_CLASSIFY_ATTEMPTS += 1

    prompt = {
        "title": entry.get("title", ""),
        "source": entry.get("source", ""),
        "url": entry.get("url", ""),
        "published_date": entry.get("published_date", ""),
        "content_excerpt": (entry.get("content") or "")[:1800],
        "deterministic_classification": {
            "kind": deterministic.get("kind"),
            "name": deterministic.get("name"),
            "org": deterministic.get("org"),
            "tag": deterministic.get("tag"),
            "note": deterministic.get("note"),
        },
    }
    body = {
        "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "input": [
            {
                "role": "system",
                "content": (
                    "Classify RSS entries for a weekly AI model/tool release dashboard. "
                    "Use only the supplied title, source, URL, and excerpt. Return JSON only with keys "
                    "include, kind, name, org, note, tag, confidence. include is true only for concrete "
                    "model releases, API releases, coding agents, agent platforms, SDKs, or AI tools/services. "
                    "Exclude tutorials, guides, case studies, customer stories, implementation advice, and "
                    "broad marketing pages unless the headline clearly announces a concrete shipped release. "
                    "The note should be one specific, dashboard-ready sentence about what shipped and why it matters."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
        "text": {"format": {"type": "json_object"}},
    }
    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("output_text") or ""
        if not text:
            chunks: list[str] = []
            for output in payload.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        chunks.append(content.get("text", ""))
            text = "".join(chunks)
        parsed = json.loads(text)
    except requests.HTTPError as exc:
        _OPENAI_CLASSIFY_FAILURES += 1
        error_payload = {}
        if exc.response is not None:
            try:
                error_payload = exc.response.json().get("error") or {}
            except (ValueError, TypeError):
                error_payload = {}
        if error_payload.get("code") in {"insufficient_quota", "invalid_api_key"} or (
            exc.response is not None and exc.response.status_code in {401, 403}
        ):
            _OPENAI_CLASSIFY_DISABLED_FOR_RUN = True
        LOGGER.warning("OpenAI model/tool classification failed for %s: %s", entry.get("url"), exc)
        return deterministic
    except (requests.RequestException, json.JSONDecodeError, TypeError, KeyError) as exc:
        _OPENAI_CLASSIFY_FAILURES += 1
        LOGGER.warning("OpenAI model/tool classification failed for %s: %s", entry.get("url"), exc)
        return deterministic

    confidence = float(parsed.get("confidence") or 0)
    kind = parsed.get("kind")
    if not parsed.get("include") or confidence < 0.7 or kind not in {"model", "tool_service"}:
        return None

    return {
        **deterministic,
        "kind": kind,
        "name": str(parsed.get("name") or deterministic["name"]).strip()[:80],
        "org": str(parsed.get("org") or deterministic["org"]).strip()[:80],
        "note": str(parsed.get("note") or deterministic["note"]).strip()[:260],
        "tag": _normalize_llm_tag(kind, str(parsed.get("tag") or deterministic["tag"])),
        "llm_confidence": confidence,
        "classifier": "llm",
    }


def _fetch_feed_entries(state: ModelToolsState) -> ModelToolsState:
    cutoff = _major_model_cutoff(window_start())
    entries: list[dict[str, Any]] = []
    for feed_url in state.get("feeds", MODEL_TOOL_CORE_FEEDS):
        LOGGER.info("Fetching model/tool feed %s", feed_url)
        feed = feedparser.parse(feed_url)
        feed_title = feed.feed.get("title", feed_url) if getattr(feed, "feed", None) else feed_url
        source = _source_name(feed_url) or feed_title
        for entry in feed.entries[:MODEL_TOOL_FEED_SCAN_LIMIT]:
            published_dt = _entry_datetime(entry)
            if published_dt and published_dt < cutoff:
                continue
            title = getattr(entry, "title", "").strip()
            url = getattr(entry, "link", "") or feed_url
            if not title or not url:
                continue
            entries.append(
                {
                    "source": source,
                    "title": title,
                    "url": url,
                    "published_date": _entry_date(entry),
                    "content": _entry_content(entry),
                    "source_url": feed_url,
                    "source_label": "RSS feed",
                }
            )
    for entry in _fetch_source_page_entries(state.get("source_pages", MODEL_TOOL_SOURCE_PAGES)):
        published_dt = None
        if entry.get("published_date"):
            try:
                published_dt = datetime.fromisoformat(entry["published_date"])
            except ValueError:
                published_dt = None
        if published_dt and published_dt.replace(tzinfo=window_start().tzinfo) < cutoff:
            continue
        entries.append(entry)
    return {**state, "entries": entries}


def _classify_entries(state: ModelToolsState) -> ModelToolsState:
    classified = []
    seen: set[str] = set()
    diagnostics = {
        "entries_considered": 0,
        "rejected_duplicate_url": 0,
        "rejected_missing_or_stale_date": 0,
        "rejected_non_release": 0,
        "rejected_by_llm": 0,
        "major_model_carried_forward": 0,
    }
    model_terms = MODEL_TOOL_CORE_MODEL_TERMS + state.get("model_terms", [])
    tool_terms = MODEL_TOOL_CORE_TOOL_SERVICE_TERMS + state.get("tool_terms", [])
    llm_error_code = (state.get("dynamic_config") or {}).get("llm_error_code")
    llm_available = llm_error_code not in {"insufficient_quota", "invalid_api_key", "missing_api_key"}
    standard_cutoff = window_start()
    oldest_cutoff = _major_model_cutoff(standard_cutoff)
    for entry in state.get("entries", []):
        diagnostics["entries_considered"] += 1
        url = entry["url"]
        if url in seen:
            diagnostics["rejected_duplicate_url"] += 1
            continue
        seen.add(url)
        entry = _resolve_entry_date(entry, oldest_cutoff)
        if not entry:
            diagnostics["rejected_missing_or_stale_date"] += 1
            continue
        release = _classify_entry(entry, model_terms=model_terms, tool_terms=tool_terms)
        if release and entry.get("source_page") and len(entry.get("content") or "") <= len(entry.get("title", "")) + 20:
            metadata = _article_metadata(url, entry.get("title", ""))
            excerpt = metadata.get("excerpt", "")
            if excerpt:
                entry = {
                    **entry,
                    "content": excerpt,
                    "published_date": metadata.get("published_date") or entry.get("published_date", ""),
                }
                release = _classify_entry(entry, model_terms=model_terms, tool_terms=tool_terms)
        if not release:
            diagnostics["rejected_non_release"] += 1
            continue
        published = _parse_datetime_value(release.get("published_date", ""))
        if published and published < standard_cutoff:
            if not release.get("major_release"):
                diagnostics["rejected_missing_or_stale_date"] += 1
                continue
            diagnostics["major_model_carried_forward"] += 1
        if release:
            release = _openai_classify_entry(entry, release, llm_available=llm_available)
        if not release:
            diagnostics["rejected_by_llm"] += 1
            continue
        classified.append(release)
    return {**state, "classified": classified, "classification_diagnostics": diagnostics}


def _release_versions(name: str) -> set[str]:
    return set(re.findall(r"\b(?:v?\d+(?:\.\d+)+|v\d+|o[134](?:-mini)?)\b", name.lower()))


def _normalized_release_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _is_near_duplicate_release(entry: dict[str, Any], existing: dict[str, Any]) -> bool:
    if entry.get("kind") != existing.get("kind"):
        return False
    if entry.get("org", "").lower() != existing.get("org", "").lower():
        return False
    if entry.get("published_date", "")[:10] != existing.get("published_date", "")[:10]:
        return False

    name = _normalized_release_name(entry.get("name", ""))
    existing_name = _normalized_release_name(existing.get("name", ""))
    if not name or not existing_name:
        return False

    versions = _release_versions(name)
    existing_versions = _release_versions(existing_name)
    if versions != existing_versions and (versions or existing_versions):
        return False
    return name == existing_name or name in existing_name or existing_name in name


def _select_entries(state: ModelToolsState) -> ModelToolsState:
    selected: list[dict[str, Any]] = []
    diagnostics = {
        "rejected_near_duplicate": 0,
        "rejected_superseded_major_model": 0,
        "major_models_selected": 0,
    }
    for kind in ("model", "tool_service"):
        entries = [entry for entry in state.get("classified", []) if entry.get("kind") == kind]
        entries.sort(
            key=lambda entry: (
                bool(entry.get("major_release")),
                entry.get("impact_score", 0),
                _parse_datetime_value(entry.get("published_date", "")) or datetime.min.replace(tzinfo=timezone.utc),
                entry.get("release_score", 0),
            ),
            reverse=True,
        )
        seen_names: set[str] = set()
        seen_major_families: set[str] = set()
        for entry in entries:
            key = _normalized_release_name(entry.get("name", ""))
            major_family = entry.get("major_model_family", "") if kind == "model" else ""
            if major_family and major_family in seen_major_families:
                diagnostics["rejected_superseded_major_model"] += 1
                continue
            if key and key in seen_names:
                diagnostics["rejected_near_duplicate"] += 1
                continue
            if any(_is_near_duplicate_release(entry, existing) for existing in selected):
                diagnostics["rejected_near_duplicate"] += 1
                continue
            if key:
                seen_names.add(key)
            if major_family:
                seen_major_families.add(major_family)
                diagnostics["major_models_selected"] += 1
            selected.append(entry)
            if len([item for item in selected if item.get("kind") == kind]) >= MODEL_TOOL_MAX_ITEMS:
                break
    return {**state, "selected": selected, "selection_diagnostics": diagnostics}


def _entry_to_item(entry: dict[str, Any]) -> Item:
    kind = entry["kind"]
    url = entry["url"]
    source_url = entry.get("source_url") or ""
    tags = [entry["tag"].lower(), kind.replace("_", "-")]
    return Item(
        id=f"{kind}-{_stable_id(url)}",
        source=entry["org"],
        source_type=kind,
        title=entry["name"],
        url=url,
        authors=[entry["org"]],
        published_date=entry.get("published_date", ""),
        fetched_date=utc_now_iso(),
        raw_content=entry.get("note", ""),
        tags=tags,
        related_links=[link for link in [source_url] if link and link != url],
        metadata={
            "item_kind": kind,
            "name": entry["name"],
            "org": entry["org"],
            "note": entry.get("note", ""),
            "tag": entry["tag"],
            "source_feed": entry.get("source", ""),
            "source_url": source_url,
            "source_label": entry.get("source_label", "Source"),
            "release_score": entry.get("release_score", 0),
            "classifier": entry.get("classifier", "deterministic"),
            "llm_confidence": entry.get("llm_confidence"),
            "major_release": bool(entry.get("major_release")),
            "major_model_family": entry.get("major_model_family", ""),
            "impact_score": entry.get("impact_score", 0),
        },
    )


def _build_items(state: ModelToolsState) -> ModelToolsState:
    return {**state, "items": [_entry_to_item(entry) for entry in state.get("selected", [])]}


def _run_sequential_graph(state: ModelToolsState) -> ModelToolsState:
    for node in (_fetch_feed_entries, _classify_entries, _select_entries, _build_items):
        state = node(state)
    return state


def _diagnostics_from_state(state: ModelToolsState) -> dict[str, Any]:
    llm_error_code = (state.get("dynamic_config") or {}).get("llm_error_code")
    disabled_by_dynamic_error = llm_error_code in {"insufficient_quota", "invalid_api_key", "missing_api_key"}
    return {
        "feeds_requested": len(state.get("feeds", [])),
        "source_pages_requested": len(state.get("source_pages", [])),
        "entries_fetched": len(state.get("entries", [])),
        "classified": len(state.get("classified", [])),
        "selected": len(state.get("selected", [])),
        "llm_classification_attempts": _OPENAI_CLASSIFY_ATTEMPTS,
        "llm_classification_failures": _OPENAI_CLASSIFY_FAILURES,
        "llm_classification_disabled": _OPENAI_CLASSIFY_DISABLED_FOR_RUN or disabled_by_dynamic_error,
        "llm_classification_skip_reason": llm_error_code if disabled_by_dynamic_error else "",
        "classification_diagnostics": state.get("classification_diagnostics", {}),
        "selection_diagnostics": state.get("selection_diagnostics", {}),
        "dynamic_config": state.get("dynamic_config", {}),
    }


def get_last_diagnostics() -> dict[str, Any] | None:
    """Return diagnostics from the most recent fetch_model_tools() call."""
    return _LAST_DIAGNOSTICS


def fetch_model_tools_with_graph(feeds: list[str] | None = None) -> list[Item]:
    """Fetch and classify model releases plus AI tools/services from RSS-style feeds."""
    global _LAST_DIAGNOSTICS
    resolved = (
        {
            "feeds": feeds,
            "source_pages": [],
            "emerging_model_terms": [],
            "emerging_tool_terms": [],
            "dynamic_config": {"source": "manual", "active_core_feeds": len(feeds)},
        }
        if feeds is not None
        else resolve_dynamic_model_tool_inputs()
    )
    initial_state: ModelToolsState = {
        "feeds": resolved.get("feeds") or MODEL_TOOL_CORE_FEEDS,
        "source_pages": resolved.get("source_pages") or MODEL_TOOL_SOURCE_PAGES,
        "model_terms": resolved.get("emerging_model_terms") or [],
        "tool_terms": resolved.get("emerging_tool_terms") or [],
        "dynamic_config": resolved.get("dynamic_config") or {},
    }
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        LOGGER.warning("langgraph is not installed; running model/tool workflow sequentially")
        result = _run_sequential_graph(initial_state)
        _LAST_DIAGNOSTICS = _diagnostics_from_state(result)
        return result.get("items", [])

    graph = StateGraph(ModelToolsState)
    graph.add_node("fetch_feed_entries", _fetch_feed_entries)
    graph.add_node("classify_entries", _classify_entries)
    graph.add_node("select_entries", _select_entries)
    graph.add_node("build_items", _build_items)
    graph.set_entry_point("fetch_feed_entries")
    graph.add_edge("fetch_feed_entries", "classify_entries")
    graph.add_edge("classify_entries", "select_entries")
    graph.add_edge("select_entries", "build_items")
    graph.add_edge("build_items", END)

    result = graph.compile().invoke(initial_state)
    _LAST_DIAGNOSTICS = _diagnostics_from_state(result)
    return result.get("items", [])


def fetch_model_tools() -> list[Item]:
    """Fetch dashboard-ready model releases and AI tool/service announcements."""
    global _OPENAI_CLASSIFY_ATTEMPTS, _OPENAI_CLASSIFY_FAILURES, _OPENAI_CLASSIFY_DISABLED_FOR_RUN
    _OPENAI_CLASSIFY_ATTEMPTS = 0
    _OPENAI_CLASSIFY_FAILURES = 0
    _OPENAI_CLASSIFY_DISABLED_FOR_RUN = False
    return fetch_model_tools_with_graph()
