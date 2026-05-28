"""arXiv paper extraction agent."""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlencode

import requests

from ..config import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS_PER_CATEGORY, window_start
from ..schema import Item, utc_now_iso
from .paper_graph import enrich_papers_with_graph

LOGGER = logging.getLogger(__name__)
ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


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
    cutoff = window_start()
    items: list[Item] = []

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
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        for entry in root.findall("atom:entry", namespaces=ATOM_NS):
            published = _parse_arxiv_date(entry.findtext("atom:published", default="", namespaces=ATOM_NS) or "")
            if published and published < cutoff:
                continue
            item = _entry_to_item(entry)
            if item:
                items.append(item)

    return enrich_papers_with_graph(items)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for paper in fetch_papers():
        print(paper.to_dict())
