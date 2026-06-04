"""Supervisor/orchestrator for the multi-agent news pipeline."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from .agents.fetch_github import fetch_github, get_last_diagnostics
from .agents.fetch_papers import fetch_papers, update_last_diagnostics
from .agents.fetch_rss import fetch_rss, get_last_diagnostics as get_rss_diagnostics
from .agents.model_tools_graph import fetch_model_tools, get_last_diagnostics as get_model_tools_diagnostics
from .dedup import deduplicate_items
from .health_log import write_health_log
from .normalize import normalize_items
from .paper_summarize import (
    enrich_paper_action_items,
    enrich_paper_summaries,
    get_last_action_diagnostics,
    get_last_summary_diagnostics,
)
from .push_to_artifact import push_to_artifact
from .quality_gate import apply_quality_gate
from .score import attach_action_scores, score_items
from .summarize import summarize_items
from .schema import Item

LOGGER = logging.getLogger(__name__)
FetchAgent = Callable[[], list[Item]]


FETCH_AGENTS: dict[str, FetchAgent] = {
    "papers": fetch_papers,
    "github": fetch_github,
    "rss": fetch_rss,
    "model_tools": fetch_model_tools,
}


def _run_agent(name: str, agent: FetchAgent) -> tuple[str, list[Item], dict]:
    started = time.perf_counter()
    try:
        items = agent()
        duration_ms = round((time.perf_counter() - started) * 1000)
        return name, items, {
            "source": name,
            "status": "ok",
            "item_count": len(items),
            "duration_ms": duration_ms,
        }
    except Exception as exc:  # noqa: BLE001 - failures are captured per source
        LOGGER.exception("Agent %s failed", name)
        duration_ms = round((time.perf_counter() - started) * 1000)
        return name, [], {
            "source": name,
            "status": "error",
            "item_count": 0,
            "duration_ms": duration_ms,
            "error": str(exc),
        }


def run_pipeline() -> dict:
    """Run the Day 1 pipeline and write the dashboard artifact."""
    all_items: list[Item] = []
    health: list[dict] = []

    with ThreadPoolExecutor(max_workers=len(FETCH_AGENTS)) as executor:
        futures = {
            executor.submit(_run_agent, name, agent): name
            for name, agent in FETCH_AGENTS.items()
        }
        for future in as_completed(futures):
            name, items, entry = future.result()
            LOGGER.info("Agent %s returned %d items", name, len(items))
            all_items.extend(items)
            if name == "github":
                from .config import GITHUB_ENABLE_EMERGING_QUERIES
                entry["query_mode"] = "core+emerging" if GITHUB_ENABLE_EMERGING_QUERIES else "core_only"
                diag = get_last_diagnostics()
                if diag:
                    entry["search_diagnostics"] = diag
            if name == "rss":
                diag = get_rss_diagnostics()
                if diag:
                    entry["fetch_diagnostics"] = diag
            if name == "model_tools":
                diag = get_model_tools_diagnostics()
                if diag:
                    entry["dynamic_config"] = diag.get("dynamic_config", {})
                    entry["extraction_diagnostics"] = diag
            health.append(entry)

    deduped = deduplicate_items(all_items)
    normalized = normalize_items(deduped)
    scored = score_items(normalized)
    passed = apply_quality_gate(scored)
    summarized = summarize_items(passed)
    enrich_paper_summaries(summarized)
    enrich_paper_action_items(summarized)
    attach_action_scores(summarized)

    paper_diagnostics = update_last_diagnostics(
        deduplicated_count=sum(item.source_type == "paper" for item in deduped),
        displayed_count=min(sum(item.get("source_type") == "paper" for item in summarized), 8),
        summary_diagnostics=get_last_summary_diagnostics(),
        action_diagnostics=get_last_action_diagnostics(),
    )
    paper_health = next((entry for entry in health if entry["source"] == "papers"), None)
    if paper_health is not None:
        paper_health["fetch_diagnostics"] = paper_diagnostics

    payload = push_to_artifact(summarized, health)
    write_health_log(health)

    LOGGER.info(
        "Fetched %d -> %d after dedup -> %d passed gate -> wrote data/output.json",
        len(all_items),
        len(deduped),
        len(passed),
    )
    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    run_pipeline()
