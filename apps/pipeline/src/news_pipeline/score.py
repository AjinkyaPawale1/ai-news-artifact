"""Relevance scoring utilities."""

from __future__ import annotations

from datetime import datetime, timezone

from .config import AI_KEYWORDS, DOMAIN_KEYWORDS
from .schema import Item


def _count_matches(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lower)


def score_items(items: list[Item]) -> list[dict]:
    """Attach a simple Day 1 score to each item."""
    scored: list[dict] = []
    for item in items:
        text = f"{item.title} {item.raw_content} {' '.join(item.tags)}"
        domain = min(_count_matches(text, DOMAIN_KEYWORDS) * 2, 10)
        ai = min(_count_matches(text, AI_KEYWORDS) * 2, 10)
        score = max(40, int((domain * 0.4 + ai * 0.6) * 10))
        record = item.to_dict()
        record["score"] = min(score, 100)
        scored.append(record)
    return sorted(scored, key=lambda item: item["score"], reverse=True)


ACTION_AI_TERMS = AI_KEYWORDS + ["ai", "machine learning", "ml", "foundation model", "multimodal"]
ACTION_PRACTICAL_TERMS = [
    "implementation",
    "framework",
    "toolkit",
    "deployment",
    "production",
    "workflow",
    "inference",
    "serving",
]
ACTION_EVIDENCE_TERMS = ["benchmark", "evaluation", "experiment", "dataset", "ablation", "baseline", "results"]
ACTION_REPRODUCIBILITY_TERMS = ["open-source", "open source", "code", "github", "repository", "dataset"]
ACTION_PRIORITY_BONUS = {"EXPERIMENT": 10, "SHARE": 8, "READ": 4, "WATCH": 2}


def _action_component(text: str, terms: list[str], weight: int, max_hits: int) -> int:
    return min(weight, round(weight * min(_count_matches(text, terms), max_hits) / max_hits))


def _action_recency(value: str) -> int:
    try:
        published = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = max(0, (datetime.now(timezone.utc) - published).days)
    return max(0, 20 - age_days * 3)


def action_score_item(item: dict) -> int:
    """Return a generic actionability score retained for paper action metadata."""
    metadata = item.get("metadata") or {}
    text = " ".join(
        [
            item.get("title", ""),
            item.get("raw_content", ""),
            " ".join(item.get("tags") or []),
        ]
    )
    components = {
        "recency": _action_recency(item.get("published_date", "")),
        "topical_fit": _action_component(text, ACTION_AI_TERMS, 25, 4),
        "applicability": _action_component(text, ACTION_PRACTICAL_TERMS, 20, 3),
        "evidence": _action_component(text, ACTION_EVIDENCE_TERMS, 15, 3),
        "reproducibility": _action_component(text, ACTION_REPRODUCIBILITY_TERMS, 10, 2),
        "priority": ACTION_PRIORITY_BONUS.get(metadata.get("priority", ""), 0),
    }
    metadata["action_score_components"] = components
    item["metadata"] = metadata
    return sum(components.values())


def attach_action_scores(items: list[dict]) -> list[dict]:
    """Attach a generic actionability score while preserving the existing ordering."""
    for item in items:
        item["action_score"] = action_score_item(item)
    return items
