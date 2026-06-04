"""Paper-only refresh path that preserves the existing dashboard checkpoint."""

from __future__ import annotations

import json
import logging
import time

from .agents.fetch_papers import fetch_papers, update_last_diagnostics
from .dedup import deduplicate_items
from .health_log import DATA_DIR, write_health_log
from .normalize import normalize_items
from .paper_summarize import (
    enrich_paper_action_items,
    enrich_paper_summaries,
    get_last_action_diagnostics,
    get_last_summary_diagnostics,
)
from .push_to_artifact import push_papers_to_existing_artifact
from .score import attach_action_scores
from .summarize import summarize_items

LOGGER = logging.getLogger(__name__)


def _load_health() -> list[dict]:
    path = DATA_DIR / "health.json"
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding="utf-8"))
    return entries if isinstance(entries, list) else []


def run_paper_pipeline() -> dict:
    """Refresh arXiv papers and retain non-paper dashboard output from the prior run."""
    started = time.perf_counter()
    papers = fetch_papers()
    deduped = deduplicate_items(papers)
    normalized = normalize_items(deduped)
    summarized = summarize_items([item.to_dict() for item in normalized])
    enrich_paper_summaries(summarized)
    enrich_paper_action_items(summarized)
    attach_action_scores(summarized)

    diagnostics = update_last_diagnostics(
        deduplicated_count=len(deduped),
        displayed_count=min(len(summarized), 8),
        summary_diagnostics=get_last_summary_diagnostics(),
        action_diagnostics=get_last_action_diagnostics(),
    )
    paper_health = {
        "source": "papers",
        "status": "ok",
        "item_count": len(summarized),
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "fetch_diagnostics": diagnostics,
    }
    health = [paper_health] + [entry for entry in _load_health() if entry.get("source") != "papers"]
    payload = push_papers_to_existing_artifact(summarized, health)
    write_health_log(health)
    LOGGER.info("Refreshed %d paper items and preserved non-paper dashboard sections", len(summarized))
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    run_paper_pipeline()
