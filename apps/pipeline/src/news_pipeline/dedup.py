"""Cross-source deduplication utilities."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .schema import Item

SPECIFIC_RELEASE_TYPES = {"model", "tool_service"}
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}
TITLE_STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}
FUZZY_TITLE_TYPES = {
    "paper": {"paper"},
    "github": {"github"},
    "release": {"model", "tool_service", "rss"},
}


def canonicalize_url(value: str) -> str:
    """Return a stable comparison form while preserving meaningful query data."""
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw.lower()
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return raw.lower()

    host = (parsed.hostname or "").lower()
    host = host.removeprefix("www.")
    try:
        port = parsed.port
    except ValueError:
        return raw.lower()
    netloc = host if port is None else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if host == "github.com" and path.endswith(".git"):
        path = path[:-4]
    if host in {"arxiv.org", "export.arxiv.org"}:
        host = "arxiv.org"
        netloc = host
        path = re.sub(r"^/pdf/", "/abs/", path)
        path = re.sub(r"\.pdf$", "", path)
        path = re.sub(r"v\d+$", "", path)
    path = path.rstrip("/") or "/"

    query = [
        (key, query_value)
        for key, query_value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    return urlunsplit(("https", netloc, path, urlencode(sorted(query)), ""))


def _normalized_title(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", (value or "").lower())
    normalized = [
        token[:-1] if len(token) > 4 and token.endswith("s") and not token.endswith("ss") else token
        for token in tokens
    ]
    return " ".join(token for token in normalized if token not in TITLE_STOP_WORDS)


def _title_family(source_type: str) -> str:
    for family, members in FUZZY_TITLE_TYPES.items():
        if source_type in members:
            return family
    return source_type


def _titles_match(left: Item, right: Item) -> bool:
    if _title_family(left.source_type) != _title_family(right.source_type):
        return False
    left_title = _normalized_title(left.title)
    right_title = _normalized_title(right.title)
    if not left_title or not right_title:
        return False
    if left_title == right_title:
        return True
    left_tokens = set(left_title.split())
    right_tokens = set(right_title.split())
    if min(len(left_tokens), len(right_tokens)) < 4:
        return False
    token_overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    sequence_similarity = SequenceMatcher(None, left_title, right_title).ratio()
    return token_overlap >= 0.8 and sequence_similarity >= 0.88


def _preference(item: Item) -> tuple[int, int, int]:
    specificity = 1 if item.source_type in SPECIFIC_RELEASE_TYPES else 0
    return specificity, len(item.raw_content or ""), len(item.metadata or {})


def _merge_links(primary: Item, duplicate: Item) -> None:
    primary_url = canonicalize_url(primary.url)
    candidates = [*primary.related_links, duplicate.url, *duplicate.related_links]
    links: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        canonical = canonicalize_url(value)
        if not canonical or canonical == primary_url or canonical in seen:
            continue
        seen.add(canonical)
        links.append(value.strip())
    primary.related_links = links


def deduplicate_items(items: list[Item]) -> list[Item]:
    """Collapse canonical-URL and high-confidence fuzzy-title duplicates."""
    deduplicated: list[Item] = []
    for item in items:
        url_key = canonicalize_url(item.url)
        if not url_key and not _normalized_title(item.title):
            continue

        match_index = next(
            (
                index
                for index, existing in enumerate(deduplicated)
                if (url_key and canonicalize_url(existing.url) == url_key) or _titles_match(existing, item)
            ),
            None,
        )
        if match_index is None:
            deduplicated.append(item)
            continue

        existing = deduplicated[match_index]
        if _preference(item) > _preference(existing):
            _merge_links(item, existing)
            deduplicated[match_index] = item
        else:
            _merge_links(existing, item)
    return deduplicated
