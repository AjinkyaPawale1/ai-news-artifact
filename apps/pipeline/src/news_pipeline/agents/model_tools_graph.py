"""LangGraph workflow for model release and AI tool/service extraction."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from html import unescape
from typing import Any, Literal, TypedDict

import feedparser

from ..config import MODEL_TOOL_FEEDS, MODEL_TOOL_MAX_ITEMS, window_start
from ..schema import Item, utc_now_iso

LOGGER = logging.getLogger(__name__)
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

ReleaseKind = Literal["model", "tool_service"]


class ModelToolsState(TypedDict, total=False):
    feeds: list[str]
    entries: list[dict[str, Any]]
    classified: list[dict[str, Any]]
    selected: list[dict[str, Any]]
    items: list[Item]


MODEL_TERMS = [
    "model",
    "gpt",
    "claude",
    "gemini",
    "llama",
    "mistral",
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
    "reasoning",
]

TOOL_SERVICE_TERMS = [
    "agent",
    "agents",
    "codex",
    "claude code",
    "copilot",
    "jules",
    "studio",
    "sdk",
    "api",
    "service",
    "platform",
    "connector",
    "tool",
    "workflow",
    "terminal",
    "ide",
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
}


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
    sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    return (sentence or title)[:150].rstrip()


def _release_score(text: str, kind: ReleaseKind) -> int:
    release_score = _term_count(text, RELEASE_TERMS) * 3
    focus_terms = MODEL_TERMS if kind == "model" else TOOL_SERVICE_TERMS
    focus_score = _term_count(text, focus_terms) * 4
    return release_score + focus_score


def _classify_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    title = entry["title"]
    content = entry["content"]
    title_text = title.lower()
    text = f"{title} {content}".lower()
    title_model_score = _term_count(title_text, MODEL_TERMS)
    title_tool_score = _term_count(title_text, TOOL_SERVICE_TERMS)
    if title_model_score == 0 and title_tool_score == 0:
        return None

    has_release_signal = _contains_any(title_text, RELEASE_TERMS) or _contains_any(text, RELEASE_TERMS)
    if not has_release_signal and max(title_model_score, title_tool_score) < 2:
        return None

    model_score = _release_score(text, "model") + title_model_score * 8
    tool_score = _release_score(text, "tool_service") + title_tool_score * 8
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
    }


def _fetch_feed_entries(state: ModelToolsState) -> ModelToolsState:
    cutoff = window_start()
    entries: list[dict[str, Any]] = []
    for feed_url in state.get("feeds", MODEL_TOOL_FEEDS):
        LOGGER.info("Fetching model/tool feed %s", feed_url)
        feed = feedparser.parse(feed_url)
        source = feed.feed.get("title", feed_url) if getattr(feed, "feed", None) else feed_url
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
                }
            )
    return {**state, "entries": entries}


def _classify_entries(state: ModelToolsState) -> ModelToolsState:
    classified = []
    seen: set[str] = set()
    for entry in state.get("entries", []):
        url = entry["url"]
        if url in seen:
            continue
        seen.add(url)
        release = _classify_entry(entry)
        if release:
            classified.append(release)
    return {**state, "classified": classified}


def _select_entries(state: ModelToolsState) -> ModelToolsState:
    selected: list[dict[str, Any]] = []
    for kind in ("model", "tool_service"):
        entries = [entry for entry in state.get("classified", []) if entry.get("kind") == kind]
        entries.sort(key=lambda entry: entry.get("release_score", 0), reverse=True)
        selected.extend(entries[:MODEL_TOOL_MAX_ITEMS])
    return {**state, "selected": selected}


def _entry_to_item(entry: dict[str, Any]) -> Item:
    kind = entry["kind"]
    url = entry["url"]
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
        metadata={
            "item_kind": kind,
            "name": entry["name"],
            "org": entry["org"],
            "note": entry.get("note", ""),
            "tag": entry["tag"],
            "source_feed": entry.get("source", ""),
            "release_score": entry.get("release_score", 0),
        },
    )


def _build_items(state: ModelToolsState) -> ModelToolsState:
    return {**state, "items": [_entry_to_item(entry) for entry in state.get("selected", [])]}


def _run_sequential_graph(state: ModelToolsState) -> ModelToolsState:
    for node in (_fetch_feed_entries, _classify_entries, _select_entries, _build_items):
        state = node(state)
    return state


def fetch_model_tools_with_graph(feeds: list[str] | None = None) -> list[Item]:
    """Fetch and classify model releases plus AI tools/services from RSS-style feeds."""
    initial_state: ModelToolsState = {"feeds": feeds or MODEL_TOOL_FEEDS}
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        LOGGER.warning("langgraph is not installed; running model/tool workflow sequentially")
        return _run_sequential_graph(initial_state).get("items", [])

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
    return result.get("items", [])


def fetch_model_tools() -> list[Item]:
    """Fetch dashboard-ready model releases and AI tool/service announcements."""
    return fetch_model_tools_with_graph()
