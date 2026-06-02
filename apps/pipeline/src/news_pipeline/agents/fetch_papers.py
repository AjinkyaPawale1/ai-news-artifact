"""arXiv paper extraction agent."""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

from ..config import ARXIV_CATEGORIES, ARXIV_FALLBACK_WINDOW_DAYS, ARXIV_MAX_RESULTS_PER_CATEGORY, window_start
from ..schema import Item, utc_now_iso
from .paper_graph import enrich_papers_with_graph

LOGGER = logging.getLogger(__name__)
ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_LAST_DIAGNOSTICS: dict = {}


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _parse_arxiv_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _entry_to_item(entry: ET.Element) -> Item | None:
    title = " ".join((entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").split())
    summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").split())
    published = entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
    url = entry.findtext("atom:id", default="", namespaces=ATOM_NS) or ""
    if not title or not url:
        return None

    authors = [
        name.text.strip()
        for name in entry.findall("atom:author/atom:name", namespaces=ATOM_NS)
        if name.text and name.text.strip()
    ]
    tags = [
        category.attrib.get("term", "").strip()
        for category in entry.findall("atom:category", namespaces=ATOM_NS)
        if category.attrib.get("term")
    ]
    pdf_url = next(
        (
            link.attrib.get("href", "")
            for link in entry.findall("atom:link", namespaces=ATOM_NS)
            if link.attrib.get("title") == "pdf"
        ),
        url,
    )

    return Item(
        id=f"paper-{_stable_id(url)}",
        source="arXiv",
        source_type="paper",
        title=title,
        url=pdf_url,
        authors=authors or ["Unknown"],
        published_date=published,
        fetched_date=utc_now_iso(),
        raw_content=summary,
        tags=tags,
    )


def fetch_papers() -> list[Item]:
    """Fetch recent AI/ML papers from arXiv."""
    global _LAST_DIAGNOSTICS

    cutoff = window_start()
    fallback_cutoff = datetime.now(timezone.utc) - timedelta(days=ARXIV_FALLBACK_WINDOW_DAYS)
    primary_items: list[Item] = []
    fallback_items: list[Item] = []
    diagnostics = {
        "categories": [],
        "raw_count": 0,
        "seven_day_count": 0,
        "fourteen_day_count": 0,
        "backfill_count": 0,
        "selected_window_days": 7,
        "deduplicated_count": 0,
        "displayed_count": 0,
    }

    for category in ARXIV_CATEGORIES:
        params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": ARXIV_MAX_RESULTS_PER_CATEGORY,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"{ARXIV_API_URL}?{urlencode(params)}"
        LOGGER.info("Fetching arXiv category %s", category)
        category_diagnostics = {
            "category": category,
            "status": "ok",
            "raw_count": 0,
            "seven_day_count": 0,
            "fourteen_day_count": 0,
        }
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            entries = root.findall("atom:entry", namespaces=ATOM_NS)
            category_diagnostics["raw_count"] = len(entries)
            diagnostics["raw_count"] += len(entries)
            for entry in entries:
                published = _parse_arxiv_date(
                    entry.findtext("atom:published", default="", namespaces=ATOM_NS) or ""
                )
                if published and published < fallback_cutoff:
                    continue
                item = _entry_to_item(entry)
                if item:
                    category_diagnostics["fourteen_day_count"] += 1
                    diagnostics["fourteen_day_count"] += 1
                    if not published or published >= cutoff:
                        primary_items.append(item)
                        category_diagnostics["seven_day_count"] += 1
                        diagnostics["seven_day_count"] += 1
                    else:
                        fallback_items.append(item)
        except (requests.RequestException, ET.ParseError) as exc:
            LOGGER.warning("Fetching arXiv category %s failed: %s", category, exc)
            category_diagnostics.update({"status": "error", "error": str(exc)})
        diagnostics["categories"].append(category_diagnostics)

    selected: dict[str, Item] = {}
    for item in primary_items:
        selected.setdefault(item.url, item)
    if len(selected) < 8:
        diagnostics["selected_window_days"] = ARXIV_FALLBACK_WINDOW_DAYS
        for item in fallback_items:
            if item.url not in selected:
                selected[item.url] = item
                diagnostics["backfill_count"] += 1
            if len(selected) >= 8:
                break

    _LAST_DIAGNOSTICS = diagnostics
    return enrich_papers_with_graph(list(selected.values()))


def update_last_diagnostics(*, deduplicated_count: int, displayed_count: int) -> dict:
    """Attach post-processing counts to diagnostics for the latest paper run."""
    _LAST_DIAGNOSTICS.update(
        {
            "deduplicated_count": deduplicated_count,
            "displayed_count": displayed_count,
        }
    )
    return get_last_diagnostics()


def get_last_diagnostics() -> dict:
    """Return diagnostics for the latest paper fetch without exposing mutable state."""
    return {
        **_LAST_DIAGNOSTICS,
        "categories": [dict(entry) for entry in _LAST_DIAGNOSTICS.get("categories", [])],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for paper in fetch_papers():
        print(paper.to_dict())
