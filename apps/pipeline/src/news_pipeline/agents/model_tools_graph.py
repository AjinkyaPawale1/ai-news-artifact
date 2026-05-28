"""LangGraph workflow for model release and AI tool/service extraction."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from html import unescape
from typing import Any, Literal, TypedDict
from urllib.parse import urljoin

import feedparser
import requests

from ..config import (
    MODEL_TOOL_FEEDS,
    MODEL_TOOL_LLM_CLASSIFY,
    MODEL_TOOL_LLM_CLASSIFY_LIMIT,
    MODEL_TOOL_MAX_ITEMS,
    MODEL_TOOL_SOURCE_PAGES,
    window_start,
)
from ..schema import Item, utc_now_iso
from .model_tools_dynamic import resolve_dynamic_model_tool_inputs

LOGGER = logging.getLogger(__name__)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
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


MODEL_TERMS = [
    "model",
    "models",
    "frontier model",
    "foundation model",
    "gpt",
    "o3",
    "o4",
    "o4-mini",
    "claude",
    "gemini",
    "gemini api",
    "llama",
    "mistral",
    "mixtral",
    "command",
    "cohere",
    "grok",
    "deepseek",
    "qwen",
    "phi",
    "gemma",
    "sonnet",
    "opus",
    "haiku",
    "embedding",
    "embeddings",
    "reasoning",
    "multimodal",
    "vision-language",
    "speech",
    "tts",
    "video model",
    "image model",
    "veo",
    "imagen",
    "sora",
    "whisper",
    "voxtral",
    "sam",
]

TOOL_SERVICE_TERMS = [
    "agent",
    "agents",
    "agentic",
    "codex",
    "claude code",
    "gemini cli",
    "antigravity",
    "copilot",
    "jules",
    "ai studio",
    "studio",
    "sdk",
    "api",
    "responses api",
    "gemini api",
    "adk",
    "agent development kit",
    "service",
    "platform",
    "connector",
    "tool",
    "tools",
    "workflow",
    "terminal",
    "ide",
    "inference",
    "serving",
    "deployment",
    "benchmark",
    "eval",
    "evaluation",
]

RELEASE_TERMS = [
    "announce",
    "announcing",
    "introduce",
    "introducing",
    "launch",
    "launched",
    "release",
    "released",
    "available",
    "generally available",
    "preview",
    "beta",
    "new",
    "upgrade",
    "updated",
    "updates",
    "rollout",
    "rolling out",
    "changelog",
]

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
}


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
    if "google" in host:
        return "Google"
    return host or url


def _date_from_text(value: str) -> str:
    match = re.search(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+20\d{2}\b",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(match.group(0).replace(".", ""), fmt).isoformat()
        except ValueError:
            continue
    return ""


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


def _article_excerpt(url: str, title: str) -> str:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.debug("Article excerpt fetch failed for %s: %s", url, exc)
        return ""

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
        if title_terms and any(term in lower for term in title_terms[:5]):
            focused.append(paragraph)
        elif not title_terms and any(term in lower for term in signal_terms):
            focused.append(paragraph)
    parts = [*focused[:4], *parser.meta_descriptions[:1]]
    return " ".join(parts)[:1800].strip()


def _fetch_source_page_entries(source_pages: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for page_url in source_pages:
        try:
            response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Source page fetch failed for %s: %s", page_url, exc)
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
    name = re.split(r"\s+[-:|]\s+", name, maxsplit=1)[0].strip()
    return name[:80] or title[:80]


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
    release_score = _term_count(text, RELEASE_TERMS) * 3
    focus_terms = MODEL_TERMS if kind == "model" else TOOL_SERVICE_TERMS
    focus_score = _term_count(text, focus_terms) * 4
    return release_score + focus_score


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
    if title_model_score == 0 and title_tool_score == 0:
        return None

    has_release_signal = (
        _contains_any(title_text, RELEASE_TERMS)
        or _contains_any(text, RELEASE_TERMS)
        or bool(entry.get("source_page"))
    )
    if not has_release_signal and max(title_model_score, title_tool_score) < 2:
        return None

    release_score = _term_count(text, RELEASE_TERMS) * 3
    model_score = release_score + _term_count(text, model_terms) * 4 + title_model_score * 8
    tool_score = release_score + _term_count(text, tool_terms) * 4 + title_tool_score * 8
    if model_score < 7 and tool_score < 7:
        return None

    kind: ReleaseKind = "model" if model_score >= tool_score else "tool_service"
    org = _org_from_source(entry["source"], text)
    return {
        **entry,
        "kind": kind,
        "name": _clean_name(title),
        "org": org,
        "note": _note(title, content),
        "tag": _model_tag(text) if kind == "model" else _tool_tag(text),
        "release_score": max(model_score, tool_score),
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
    global _OPENAI_CLASSIFY_ATTEMPTS, _OPENAI_CLASSIFY_FAILURES, _OPENAI_CLASSIFY_DISABLED_FOR_RUN  # noqa: PLW0603
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
    cutoff = window_start()
    entries: list[dict[str, Any]] = []
    for feed_url in state.get("feeds", MODEL_TOOL_FEEDS):
        LOGGER.info("Fetching model/tool feed %s", feed_url)
        feed = feedparser.parse(feed_url)
        feed_title = feed.feed.get("title", feed_url) if getattr(feed, "feed", None) else feed_url
        source = _source_name(feed_url) or feed_title
        for entry in feed.entries[:MODEL_TOOL_MAX_ITEMS * 3]:
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
    model_terms = MODEL_TERMS + state.get("model_terms", [])
    tool_terms = TOOL_SERVICE_TERMS + state.get("tool_terms", [])
    llm_error_code = (state.get("dynamic_config") or {}).get("llm_error_code")
    llm_available = llm_error_code not in {"insufficient_quota", "invalid_api_key", "missing_api_key"}
    for entry in state.get("entries", []):
        url = entry["url"]
        if url in seen:
            continue
        seen.add(url)
        release = _classify_entry(entry, model_terms=model_terms, tool_terms=tool_terms)
        if release and entry.get("source_page") and len(entry.get("content") or "") <= len(entry.get("title", "")) + 20:
            excerpt = _article_excerpt(url, entry.get("title", ""))
            if excerpt:
                entry = {**entry, "content": excerpt}
                release = _classify_entry(entry, model_terms=model_terms, tool_terms=tool_terms)
        if release:
            release = _openai_classify_entry(entry, release, llm_available=llm_available)
        if release:
            classified.append(release)
    return {**state, "classified": classified}


def _select_entries(state: ModelToolsState) -> ModelToolsState:
    selected: list[dict[str, Any]] = []
    for kind in ("model", "tool_service"):
        entries = [entry for entry in state.get("classified", []) if entry.get("kind") == kind]
        entries.sort(key=lambda entry: entry.get("release_score", 0), reverse=True)
        seen_names: set[str] = set()
        for entry in entries:
            key = re.sub(r"[^a-z0-9]+", " ", entry.get("name", "").lower()).strip()
            if key and key in seen_names:
                continue
            if key:
                seen_names.add(key)
            selected.append(entry)
            if len([item for item in selected if item.get("kind") == kind]) >= MODEL_TOOL_MAX_ITEMS:
                break
    return {**state, "selected": selected}


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
        "dynamic_config": state.get("dynamic_config", {}),
    }


def get_last_diagnostics() -> dict[str, Any] | None:
    """Return diagnostics from the most recent fetch_model_tools() call."""
    return _LAST_DIAGNOSTICS


def fetch_model_tools_with_graph(feeds: list[str] | None = None) -> list[Item]:
    """Fetch and classify model releases plus AI tools/services from RSS-style feeds."""
    global _LAST_DIAGNOSTICS  # noqa: PLW0603
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
        "feeds": resolved.get("feeds") or MODEL_TOOL_FEEDS,
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
    global _OPENAI_CLASSIFY_ATTEMPTS, _OPENAI_CLASSIFY_FAILURES, _OPENAI_CLASSIFY_DISABLED_FOR_RUN  # noqa: PLW0603
    _OPENAI_CLASSIFY_ATTEMPTS = 0
    _OPENAI_CLASSIFY_FAILURES = 0
    _OPENAI_CLASSIFY_DISABLED_FOR_RUN = False
    return fetch_model_tools_with_graph()
