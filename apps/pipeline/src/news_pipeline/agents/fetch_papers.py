"""arXiv paper extraction agent facade."""

from __future__ import annotations

import logging

from ..config import ARXIV_CATEGORIES
from ..schema import Item
from .paper_graph import fetch_papers_with_graph

LOGGER = logging.getLogger(__name__)
_LAST_DIAGNOSTICS: dict = {}


def fetch_papers() -> list[Item]:
    """Fetch, select, and enrich recent AI/ML papers from arXiv."""
    global _LAST_DIAGNOSTICS

    papers, diagnostics = fetch_papers_with_graph(list(ARXIV_CATEGORIES))
    _LAST_DIAGNOSTICS = diagnostics
    return papers


def update_last_diagnostics(
    *,
    deduplicated_count: int,
    displayed_count: int,
    summary_diagnostics: dict | None = None,
    action_diagnostics: dict | None = None,
) -> dict:
    """Attach post-processing counts to diagnostics for the latest paper run."""
    _LAST_DIAGNOSTICS.update(
        {
            "deduplicated_count": deduplicated_count,
            "displayed_count": displayed_count,
        }
    )
    if summary_diagnostics is not None:
        _LAST_DIAGNOSTICS["summary_diagnostics"] = dict(summary_diagnostics)
    if action_diagnostics is not None:
        _LAST_DIAGNOSTICS["action_diagnostics"] = dict(action_diagnostics)
    return get_last_diagnostics()


def get_last_diagnostics() -> dict:
    """Return diagnostics for the latest paper fetch without exposing mutable state."""
    return {
        **_LAST_DIAGNOSTICS,
        "categories": [dict(entry) for entry in _LAST_DIAGNOSTICS.get("categories", [])],
        "summary_diagnostics": dict(_LAST_DIAGNOSTICS.get("summary_diagnostics", {})),
        "action_diagnostics": dict(_LAST_DIAGNOSTICS.get("action_diagnostics", {})),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for paper in fetch_papers():
        print(paper.to_dict())
