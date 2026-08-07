"""Write pipeline output to the dashboard artifact."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import ARXIV_CATEGORIES, GITHUB_REPOS_EVERGREEN, RSS_FEEDS
from .model_tools_config import MODEL_TOOL_KNOWN_BENCHMARK_URLS, MODEL_TOOL_MAX_ITEMS, MODEL_TOOL_SOURCE_PAGES

DATA_DIR = Path(__file__).resolve().parents[4] / "data"
OUTPUT_PATH = DATA_DIR / "output.json"
ARCHIVE_DIR = DATA_DIR / "archive"
ARCHIVE_INDEX_PATH = ARCHIVE_DIR / "index.json"
PUBLICATION_TIMEZONE = ZoneInfo("America/New_York")
MODEL_BENCHMARK_URL = "https://artificialanalysis.ai/evaluations"
ARTIFICIAL_ANALYSIS_MODELS_URL = "https://artificialanalysis.ai/models"
FALLBACK_MAX_AGE_DAYS = 28
FALLBACK_SECTIONS = {
    "papers": "papers",
    "repos": "github",
    "models": "model_tools",
    "toolsServices": "model_tools",
    "blogs": "rss",
}


def _format_date(value: str) -> str:
    if not value:
        return "Unknown"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%b %-d, %Y")
    except ValueError:
        return value[:16]


def _format_count(value: int | str | None) -> str:
    if isinstance(value, str):
        return value
    value = value or 0
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _publication_monday(generated_at: str) -> str:
    generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    local_date = generated.astimezone(PUBLICATION_TIMEZONE).date()
    return (local_date - timedelta(days=local_date.weekday())).isoformat()


def archive_dashboard_payload(payload: dict, health: list[dict]) -> dict:
    """Store an idempotent weekly snapshot and refresh the archive manifest."""
    archive_date = _publication_monday(payload["generatedAt"])
    edition_dir = ARCHIVE_DIR / archive_date
    edition_dir.mkdir(parents=True, exist_ok=True)

    output_path = edition_dir / "output.json"
    health_path = edition_dir / "health.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    health_path.write_text(json.dumps(health, indent=2), encoding="utf-8")

    existing = []
    if ARCHIVE_INDEX_PATH.exists():
        parsed = json.loads(ARCHIVE_INDEX_PATH.read_text(encoding="utf-8"))
        existing = parsed.get("editions", []) if isinstance(parsed, dict) else []

    edition = {
        "date": archive_date,
        "generatedAt": payload["generatedAt"],
        "outputPath": f"archive/{archive_date}/output.json",
        "healthPath": f"archive/{archive_date}/health.json",
    }
    editions = [entry for entry in existing if entry.get("date") != archive_date]
    editions.append(edition)
    editions.sort(key=lambda entry: entry.get("date", ""), reverse=True)
    index = {"editions": editions}
    ARCHIVE_INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return edition


def _load_payload(path: Path) -> dict | None:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _fallback_candidates() -> list[dict]:
    """Return the current artifact then archived editions, newest first."""
    candidates: list[dict] = []
    seen_generated_at: set[str] = set()

    def add(path: Path) -> None:
        payload = _load_payload(path)
        generated_at = payload.get("generatedAt") if payload else ""
        if not payload or not generated_at or generated_at in seen_generated_at:
            return
        seen_generated_at.add(generated_at)
        candidates.append(payload)

    if OUTPUT_PATH.exists():
        add(OUTPUT_PATH)
    index = _load_payload(ARCHIVE_INDEX_PATH) or {}
    editions = index.get("editions") if isinstance(index, dict) else []
    for edition in editions if isinstance(editions, list) else []:
        if not isinstance(edition, dict):
            continue
        output_path = edition.get("outputPath")
        if isinstance(output_path, str):
            add(DATA_DIR / output_path)
    return candidates


def _valid_fallback_item(section: str, item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if section == "papers":
        return bool(item.get("title") and item.get("url"))
    if section == "repos":
        return bool(item.get("name") and item.get("url"))
    if section in {"models", "toolsServices"}:
        return bool(item.get("name") and item.get("url") and item.get("note"))
    if section == "blogs":
        summary = " ".join(item.get("takeaways") or [])
        normalized_summary = " ".join(summary.split())
        return bool(
            item.get("title")
            and item.get("url")
            and item.get("linkVerified")
            and len(normalized_summary) >= 120
            and normalized_summary.endswith((".", "!", "?"))
        )
    return False


def _fallback_section_items(payload: dict, section: str) -> list[dict]:
    items = payload.get(section)
    if not isinstance(items, list):
        return []
    return [item for item in items if _valid_fallback_item(section, item)]


def _source_was_healthy(payload: dict, section: str) -> bool:
    existing_fallbacks = payload.get("fallbackSections") or {}
    if isinstance(existing_fallbacks, dict) and isinstance(existing_fallbacks.get(section), dict):
        return True
    source = FALLBACK_SECTIONS[section]
    return any(
        entry.get("source") == source and entry.get("status") == "ok"
        for entry in payload.get("health") or []
        if isinstance(entry, dict)
    )


def _fallback_provenance(payload: dict, section: str) -> dict | None:
    existing_fallbacks = payload.get("fallbackSections") or {}
    existing = existing_fallbacks.get(section) if isinstance(existing_fallbacks, dict) else None
    if isinstance(existing, dict) and existing.get("editionDate") and existing.get("generatedAt"):
        return {
            "editionDate": existing["editionDate"],
            "generatedAt": existing["generatedAt"],
        }
    generated_at = payload.get("generatedAt")
    if not isinstance(generated_at, str):
        return None
    try:
        return {
            "editionDate": _publication_monday(generated_at),
            "generatedAt": generated_at,
        }
    except ValueError:
        return None


def _is_within_fallback_window(current_date: str, provenance: dict) -> bool:
    try:
        current = date.fromisoformat(current_date)
        source = date.fromisoformat(provenance["editionDate"])
    except (KeyError, TypeError, ValueError):
        return False
    age = (current - source).days
    return 0 <= age <= FALLBACK_MAX_AGE_DAYS


def apply_section_fallbacks(payload: dict) -> dict:
    """Fill empty dashboard sections from the latest structurally valid prior artifact."""
    updated = dict(payload)
    fallback_sections: dict[str, dict] = {}
    current_edition_date = _publication_monday(payload["generatedAt"])
    candidates = _fallback_candidates()

    for section in FALLBACK_SECTIONS:
        if _fallback_section_items(payload, section):
            continue
        for candidate in candidates:
            if not _source_was_healthy(candidate, section):
                continue
            provenance = _fallback_provenance(candidate, section)
            items = _fallback_section_items(candidate, section)
            if not provenance or not items or not _is_within_fallback_window(current_edition_date, provenance):
                continue
            updated[section] = items
            fallback_sections[section] = {
                **provenance,
                "reason": "no_current_valid_items",
            }
            break

    updated["fallbackSections"] = fallback_sections
    return updated


def _normalized_benchmark_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _artificial_analysis_model_url(name: str) -> str:
    normalized = _normalized_benchmark_name(name)
    return MODEL_TOOL_KNOWN_BENCHMARK_URLS.get(normalized, ARTIFICIAL_ANALYSIS_MODELS_URL)


def _to_action_item(item: dict, priority: str) -> dict:
    metadata = item.get("metadata") or {}
    action_items = metadata.get("action_items") or []
    takeaways = metadata.get("takeaways") or []
    return {
        "priority": metadata.get("priority") or priority,
        "title": action_items[0] if action_items else item.get("title", "Untitled"),
        "source": item.get("source", "Unknown"),
        "sourceMeta": item.get("source_type", "source").upper(),
        "date": _format_date(item.get("published_date", "")),
        "why": (
            takeaways[0]
            if takeaways
            else item.get("summary") or item.get("raw_content") or "No summary available yet."
        ),
        "tags": item.get("tags") or [item.get("source_type", "AI")],
        "score": item.get("action_score", item.get("score", 50)),
        "url": item.get("url", ""),
    }


def _to_paper(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    return {
        "title": item.get("title", "Untitled"),
        "authors": ", ".join(item.get("authors") or ["Unknown"]),
        "org": item.get("source", "arXiv"),
        "date": _format_date(item.get("published_date", "")),
        "hasCode": bool(metadata.get("has_code")),
        "stars": 0,
        "researchScore": metadata.get("research_score", 0),
        "priority": metadata.get("priority", "READ"),
        "tags": metadata.get("paper_tags") or ["AI Research"],
        "abstract": item.get("raw_content") or item.get("summary") or "No abstract available.",
        "takeaways": metadata.get("takeaways")
        or [item.get("summary") or "Review this paper for potential relevance."],
        "actionItems": metadata.get("action_items") or [],
        "researchSignals": metadata.get("research_signals")
        or {"evidence": "Low", "applicability": "Low", "reproducibility": "Low", "novelty": "Low"},
        "capability": metadata.get("capability", "Other AI/ML"),
        "domain": metadata.get("domain", "Other"),
        "enterpriseScore": item.get("enterprise_score", 0),
        "enterpriseSignals": metadata.get("enterprise_signal_components") or {},
        "url": item.get("url", ""),
    }


def _to_blog(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    return {
        "source": item.get("source", "RSS"),
        "title": item.get("title", "Untitled"),
        "tag": (item.get("tags") or ["AI"])[0][:14].upper(),
        "date": _format_date(item.get("published_date", "")),
        "takeaways": [item.get("summary") or item.get("raw_content") or "Review this update."],
        "url": item.get("url", ""),
        "linkVerified": bool(metadata.get("link_verified")),
        "enterpriseScore": item.get("enterprise_score", 0),
    }


def _to_repo(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    return {
        "name": item.get("title", "unknown/repo"),
        "stars": _format_count(metadata.get("stars")),
        "desc": item.get("raw_content") or item.get("summary") or "GitHub update",
        "url": item.get("url", ""),
        "language": metadata.get("language", ""),
        "topics": item.get("tags") or [],
        "createdAt": _format_date(metadata.get("created_at", "")),
        "lastUpdated": _format_date(metadata.get("pushed_at") or item.get("published_date", "")),
        "fetchedAt": _format_date(metadata.get("fetched_at") or item.get("fetched_date", "")),
        "bestFor": metadata.get("best_for", "AI Engineering"),
        "bullets": metadata.get("bullets") or [item.get("summary") or "Review this repository."],
        "actionItems": metadata.get("action_items") or [],
        "latestRelease": metadata.get("latest_release", ""),
        "latestReleaseUrl": metadata.get("latest_release_url", ""),
        "homepage": metadata.get("homepage", ""),
        "license": metadata.get("license", ""),
        "enterpriseScore": item.get("enterprise_score", 0),
    }


def _to_release(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    name = metadata.get("name") or item.get("title", "Untitled")
    release_url = item.get("url", "")
    source_url = metadata.get("source_url", "")
    benchmark_url = metadata.get("benchmark_url", "")
    if item.get("source_type") == "model" and not benchmark_url:
        benchmark_url = _artificial_analysis_model_url(name)
    links = []
    if release_url:
        links.append({"label": "Read release", "url": release_url})
    if item.get("source_type") == "model" and benchmark_url:
        benchmark_label = "Model directory" if benchmark_url == ARTIFICIAL_ANALYSIS_MODELS_URL else "Benchmark"
        links.append({"label": benchmark_label, "url": benchmark_url})
    return {
        "name": name,
        "org": metadata.get("org") or item.get("source", "AI"),
        "date": _format_date(item.get("published_date", "")),
        "note": metadata.get("note") or item.get("summary") or item.get("raw_content") or "Review this release.",
        "tag": metadata.get("tag") or ((item.get("tags") or ["AI"])[0][:10].upper()),
        "url": release_url,
        "sourceUrl": source_url,
        "sourceLabel": metadata.get("source_label", "Source"),
        "benchmarkUrl": benchmark_url,
        "links": links,
        "enterpriseScore": item.get("enterprise_score", 0),
    }


def _repo_cluster(item: dict) -> str:
    text = " ".join(
        [
            item.get("title", ""),
            item.get("raw_content", ""),
            " ".join(item.get("tags") or []),
        ]
    ).lower()
    if any(term in text for term in ("memory", "knowledge graph", "knowledge management", "second brain")):
        return "agent_memory"
    return ""


def _select_diverse_repos(items: list[dict], limit: int = 8) -> list[dict]:
    selected: list[dict] = []
    cluster_counts: dict[str, int] = {}
    for item in items:
        cluster = _repo_cluster(item)
        if cluster and cluster_counts.get(cluster, 0) >= 2:
            continue
        selected.append(item)
        if cluster:
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def _current_sources() -> dict:
    return {
        "papers": {"label": "arXiv categories", "items": list(ARXIV_CATEGORIES)},
        "github": {"label": "Watched repositories", "items": list(GITHUB_REPOS_EVERGREEN)},
        "rss": {"label": "Official blogs", "items": list(RSS_FEEDS)},
        "modelTools": {"label": "Official release pages", "items": list(MODEL_TOOL_SOURCE_PAGES)},
    }


def build_dashboard_payload(items: list[dict], health: list[dict] | None = None) -> dict:
    """Build the JSON shape consumed by the React dashboard."""
    papers = [item for item in items if item.get("source_type") == "paper"]
    papers.sort(key=lambda item: (item.get("metadata") or {}).get("research_score", 0), reverse=True)
    github = [
        item
        for item in items
        if item.get("source_type") == "github"
        and (item.get("metadata") or {}).get("item_kind", "repo") == "repo"
    ]
    github.sort(
        key=lambda item: (
            (item.get("metadata") or {}).get("traction_score", 0),
            (item.get("metadata") or {}).get("stars", 0),
        ),
        reverse=True,
    )
    rss = [item for item in items if item.get("source_type") == "rss"]
    models = [item for item in items if item.get("source_type") == "model"]
    tools_services = [item for item in items if item.get("source_type") == "tool_service"]
    top_papers = papers[:5]
    priorities = ["READ", "EXPERIMENT", "SHARE", "WATCH", "READ"]
    health_entries = health or []
    healthy_sources = sum(entry.get("status") == "ok" for entry in health_entries)
    source_total = len(health_entries)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "stats": [
            {"label": "PAPERS REVIEWED", "value": str(len(papers)), "sub": f"{min(len(papers), 8)} selected"},
            {"label": "REPOS INDEXED", "value": str(len(github)), "sub": f"{min(len(github), 8)} shown"},
            {
                "label": "RELEASES TRACKED",
                "value": str(len(models) + len(tools_services)),
                "sub": f"{len(models)} models · {len(tools_services)} tools",
            },
            {
                "label": "HEALTHY SOURCES",
                "value": f"{healthy_sources}/{source_total}" if source_total else "—",
                "sub": "latest pipeline run" if source_total else "run pipeline to populate",
                "accent": True,
            },
        ],
        "actionItems": [
            _to_action_item(item, priorities[index % len(priorities)])
            for index, item in enumerate(top_papers)
        ],
        "repos": [_to_repo(item) for item in _select_diverse_repos(github)],
        "models": [_to_release(item) for item in models[:MODEL_TOOL_MAX_ITEMS]],
        "toolsServices": [_to_release(item) for item in tools_services[:MODEL_TOOL_MAX_ITEMS]],
        "papers": [_to_paper(item) for item in papers[:8]],
        "blogs": [_to_blog(item) for item in rss[:10]],
        "fallbackSections": {},
        "socialPosts": [],
        "trending": [],
        "health": health_entries,
        "sources": _current_sources(),
    }


def update_papers_in_payload(payload: dict, papers: list[dict], health: list[dict]) -> dict:
    """Refresh paper-owned artifact fields while preserving other dashboard sections."""
    ranked = sorted(
        papers,
        key=lambda item: (item.get("metadata") or {}).get("research_score", 0),
        reverse=True,
    )
    updated = dict(payload)
    stats = [dict(entry) for entry in payload.get("stats", [])]
    paper_stat = next(
        (entry for entry in stats if entry.get("label") in {"PAPERS REVIEWED", "PAPERS SCANNED"}),
        None,
    )
    if paper_stat is None:
        stats.insert(0, {"label": "PAPERS REVIEWED", "value": str(len(ranked)), "sub": f"{min(len(ranked), 8)} selected"})
    else:
        paper_stat.update({"label": "PAPERS REVIEWED", "value": str(len(ranked)), "sub": f"{min(len(ranked), 8)} selected"})

    updated.update(
        {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "actionItems": [
                _to_action_item(item, ["READ", "EXPERIMENT", "SHARE", "WATCH", "READ"][index])
                for index, item in enumerate(ranked[:5])
            ],
            "papers": [_to_paper(item) for item in ranked[:8]],
            "health": health,
        }
    )
    return updated


def push_to_artifact(items: list[dict], health: list[dict] | None = None) -> dict:
    """Write final dashboard payload to data/output.json."""
    DATA_DIR.mkdir(exist_ok=True)
    health_entries = health or []
    payload = apply_section_fallbacks(build_dashboard_payload(items, health_entries))
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    archive_dashboard_payload(payload, health_entries)
    return payload


def push_papers_to_existing_artifact(papers: list[dict], health: list[dict]) -> dict:
    """Write a paper-only refresh without replacing non-paper dashboard sections."""
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8")) if OUTPUT_PATH.exists() else {}
    updated = update_papers_in_payload(payload, papers, health)
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    return updated
