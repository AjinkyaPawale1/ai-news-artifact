"""Write pipeline output to the dashboard artifact."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data"
OUTPUT_PATH = DATA_DIR / "output.json"


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
        "score": item.get("score", 50),
        "fsoRelevant": True,
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
        "score": item.get("score", 50),
        "verticals": metadata.get("verticals") or ["AI", "Research"],
        "fsoRelevant": True,
        "abstract": item.get("raw_content") or item.get("summary") or "No abstract available.",
        "takeaways": metadata.get("takeaways")
        or [item.get("summary") or "Review this paper for potential relevance."],
        "actionItems": metadata.get("action_items") or [],
        "relevance": metadata.get("relevance")
        or {"wam": "Medium", "cm": "Medium", "ins": "Low", "risk": "Medium"},
        "url": item.get("url", ""),
    }


def _to_blog(item: dict) -> dict:
    return {
        "source": item.get("source", "RSS"),
        "title": item.get("title", "Untitled"),
        "tag": (item.get("tags") or ["AI"])[0][:14].upper(),
        "date": _format_date(item.get("published_date", "")),
        "fsoRelevant": True,
        "takeaways": [item.get("summary") or item.get("raw_content") or "Review this update."],
        "url": item.get("url", ""),
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
        "latestRelease": metadata.get("latest_release", ""),
        "latestReleaseUrl": metadata.get("latest_release_url", ""),
        "homepage": metadata.get("homepage", ""),
        "license": metadata.get("license", ""),
    }


def build_dashboard_payload(items: list[dict], health: list[dict] | None = None) -> dict:
    """Build the JSON shape consumed by the React dashboard."""
    papers = [item for item in items if item.get("source_type") == "paper"]
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
    top = items[:5]
    priorities = ["READ", "EXPERIMENT", "SHARE", "WATCH", "READ"]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "stats": [
            {"label": "PAPERS SCANNED", "value": str(len(papers)), "sub": "arXiv"},
            {"label": "REPOS INDEXED", "value": str(len(github)), "sub": f"{min(len(github), 8)} shown"},
            {"label": "ARTICLES", "value": str(len(rss)), "sub": "RSS feeds"},
            {"label": "FSO-RELEVANT", "value": str(len(items)), "sub": "score ≥ 40", "accent": True},
        ],
        "actionItems": [_to_action_item(item, priorities[index % len(priorities)]) for index, item in enumerate(top)],
        "repos": [_to_repo(item) for item in github[:8]],
        "models": [],
        "toolsServices": [],
        "papers": [_to_paper(item) for item in papers[:10]],
        "blogs": [_to_blog(item) for item in rss[:10]],
        "socialPosts": [],
        "trending": [],
        "health": health or [],
    }


def push_to_artifact(items: list[dict], health: list[dict] | None = None) -> dict:
    """Write final dashboard payload to data/output.json."""
    DATA_DIR.mkdir(exist_ok=True)
    payload = build_dashboard_payload(items, health)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
