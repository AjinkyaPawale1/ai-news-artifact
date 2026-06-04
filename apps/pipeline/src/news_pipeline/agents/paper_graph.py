"""LangGraph workflow for deterministic paper enrichment and ranking."""

from __future__ import annotations

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict
from urllib.parse import urlencode

import requests

from ..config import (
    ARXIV_FALLBACK_WINDOW_DAYS,
    ARXIV_MAX_RESULTS_PER_CATEGORY,
    ARXIV_MAX_RETRIES,
    ARXIV_REQUEST_INTERVAL_SECONDS,
    window_start,
)
from ..retry import retry_with_exponential_backoff
from ..schema import Item
from ..schema import utc_now_iso

LOGGER = logging.getLogger(__name__)
ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_RETRYABLE_STATUS_CODES = {408, 425, 429}
_LAST_ARXIV_REQUEST_AT: float | None = None
WeightedTerm = tuple[str, int]


class PaperGraphState(TypedDict, total=False):
    categories: list[str]
    primary_items: list[Item]
    fallback_items: list[Item]
    selected: list[Item]
    enriched: list[Item]
    diagnostics: dict[str, Any]


CAPABILITY_KEYWORDS = [
    (
        "Agentic AI",
        [("multi-agent", 4), ("multiagent", 4), ("agentic", 4), ("tool use", 3), ("agents", 2), ("agent", 2)],
    ),
    (
        "RAG and Knowledge Systems",
        [
            ("retrieval augmented generation", 5),
            ("knowledge graph", 4),
            ("knowledge base", 4),
            ("embedding", 2),
            ("retrieval", 2),
            ("vector", 1),
            ("rag", 4),
        ],
    ),
    (
        "Foundation Models and Generative AI",
        [
            ("foundation model", 4),
            ("language model", 3),
            ("generative ai", 3),
            ("transformer", 2),
            ("diffusion", 2),
            ("llm", 3),
        ],
    ),
    (
        "Reasoning and Planning",
        [("chain-of-thought", 4), ("reasoning", 3), ("planning", 3), ("mathematical", 2), ("logic", 2)],
    ),
    (
        "Evaluation and Benchmarks",
        [("benchmark", 2), ("evaluation", 2), ("leaderboard", 2), ("metric", 1), ("measure", 1), ("eval", 1)],
    ),
    (
        "Multimodal AI",
        [
            ("vision-language", 4),
            ("multimodal", 4),
            ("modality", 3),
            ("point cloud", 3),
            ("image", 1),
            ("audio", 1),
            ("video", 1),
            ("vlm", 3),
        ],
    ),
    (
        "Training and Fine-Tuning",
        [
            ("reinforcement learning", 4),
            ("fine-tuning", 3),
            ("finetuning", 3),
            ("alignment", 2),
            ("training", 1),
            ("rlhf", 3),
        ],
    ),
    (
        "Inference and Model Efficiency",
        [
            ("quantization", 3),
            ("distillation", 3),
            ("compression", 3),
            ("inference", 2),
            ("latency", 2),
            ("serving", 2),
            ("efficient", 1),
        ],
    ),
    (
        "LLMOps and Production AI",
        [
            ("observability", 3),
            ("orchestration", 3),
            ("deployment", 2),
            ("monitoring", 2),
            ("production", 2),
            ("llmops", 4),
        ],
    ),
    (
        "Safety, Alignment and Governance",
        [
            ("responsible ai", 4),
            ("governance", 3),
            ("adversarial", 3),
            ("security", 3),
            ("privacy", 3),
            ("safety", 3),
            ("alignment", 2),
        ],
    ),
    (
        "Data and Synthetic Data",
        [("synthetic data", 4), ("data quality", 3), ("data generation", 3), ("dataset", 2), ("labeling", 2)],
    ),
    (
        "Classical ML and Predictive Modeling",
        [
            ("machine learning", 3),
            ("forecasting", 3),
            ("classification", 2),
            ("regression", 2),
            ("clustering", 2),
            ("predictive", 2),
        ],
    ),
]

DOMAIN_KEYWORDS = [
    (
        "AI Engineering and Developer Tools",
        [
            ("developer tools", 5),
            ("software engineering", 5),
            ("coding agent", 4),
            ("code generation", 4),
            ("orchestration", 3),
            ("developer", 3),
            ("coding", 3),
            ("toolkit", 2),
            ("llmops", 4),
        ],
    ),
    (
        "Enterprise and Knowledge Work",
        [
            ("customer support", 4),
            ("knowledge work", 4),
            ("enterprise", 3),
            ("productivity", 3),
            ("document workflow", 3),
        ],
    ),
    (
        "Security and Privacy",
        [("cybersecurity", 4), ("adversarial attack", 4), ("security", 3), ("privacy", 3), ("cyber", 3)],
    ),
    (
        "Healthcare and Life Sciences",
        [
            ("life sciences", 4),
            ("hospital", 4),
            ("clinical", 4),
            ("patient", 3),
            ("medical", 3),
            ("biology", 3),
            ("nicu", 4),
            ("drug", 2),
        ],
    ),
    (
        "Finance and Economics",
        [
            ("real estate", 4),
            ("capital markets", 4),
            ("portfolio", 3),
            ("trading", 3),
            ("financial", 3),
            ("finance", 3),
            ("economic", 3),
            ("bank", 3),
        ],
    ),
    (
        "Robotics and Autonomous Systems",
        [
            ("spatial intelligence", 5),
            ("embodied", 4),
            ("autonomous system", 4),
            ("robotics", 4),
            ("navigation", 3),
            ("robot", 3),
        ],
    ),
    ("Science and Research", [("laboratory", 4), ("scientific", 3), ("science", 3)]),
    ("Education", [("education", 4), ("student", 3), ("teaching assistant", 4), ("tutor", 3)]),
    (
        "Media and Creative",
        [("video generation", 4), ("image generation", 4), ("creative", 3), ("music", 3), ("media", 3)],
    ),
    (
        "Public Sector and Legal",
        [("public sector", 4), ("government", 3), ("legal", 3), ("law", 3)],
    ),
    ("Cross-domain", [("general-purpose", 3), ("cross-domain", 4), ("multi-domain", 4), ("generalizable", 2)]),
]

AI_ML_TERMS = [
    "ai",
    "artificial intelligence",
    "machine learning",
    "ml",
    "llm",
    "language model",
    "generative",
    "agent",
    "retrieval",
    "transformer",
    "neural",
    "multimodal",
    "reasoning",
]
EVIDENCE_TERMS = [
    "benchmark",
    "evaluation",
    "experiment",
    "dataset",
    "ablation",
    "baseline",
    "accuracy",
    "results",
    "metric",
    "study",
]
APPLICABILITY_TERMS = [
    "implementation",
    "framework",
    "toolkit",
    "system",
    "deployment",
    "production",
    "workflow",
    "latency",
    "inference",
    "serving",
]
REPRODUCIBILITY_TERMS = [
    "open-source",
    "open source",
    "code",
    "github",
    "repository",
    "dataset",
    "implementation",
    "reproduc",
]
NOVELTY_TERMS = [
    "novel",
    "new",
    "introduce",
    "propose",
    "first",
    "state-of-the-art",
    "sota",
    "emerging",
]
SHARE_TERMS = [
    "safety",
    "governance",
    "responsible ai",
    "privacy",
    "security",
    "general-purpose",
    "widely applicable",
    "cross-domain",
]
WATCH_TERMS = ["survey", "position", "future work", "limitations", "preliminary", "early results"]


def _paper_text(item: Item) -> str:
    return " ".join([item.title, item.raw_content, " ".join(item.tags)]).lower()


def _matches(text: str, keywords: list[str]) -> int:
    return _weighted_matches(text, [(keyword, 1) for keyword in keywords])


def _phrase_pattern(phrase: str) -> re.Pattern:
    escaped = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)")


def _weighted_matches(text: str, terms: list[WeightedTerm]) -> int:
    """Count non-overlapping phrase matches, preferring specific terms."""
    occupied: list[tuple[int, int]] = []
    score = 0
    for phrase, weight in sorted(terms, key=lambda term: (len(term[0]), term[1]), reverse=True):
        for match in _phrase_pattern(phrase).finditer(text):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in occupied):
                continue
            occupied.append(span)
            score += weight
            break
    return score


def _best_label(
    text: str,
    groups: list[tuple[str, list[WeightedTerm]]],
    fallback: str,
    *,
    min_score: int = 1,
    reject_ties: bool = False,
) -> str:
    scored = [(label, _weighted_matches(text, keywords)) for label, keywords in groups]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    label, score = scored[0]
    if score < min_score or (reject_ties and len(scored) > 1 and scored[1][1] == score):
        return fallback
    return label


def _component_score(text: str, terms: list[str], weight: int, max_hits: int) -> int:
    return min(weight, round(weight * min(_matches(text, terms), max_hits) / max_hits))


def _recency_score(item: Item) -> int:
    try:
        published = datetime.fromisoformat(item.published_date.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = max(0, (datetime.now(timezone.utc) - published).days)
    return max(0, 10 - age_days)


def _signal_level(score: int, weight: int) -> str:
    ratio = score / weight
    if ratio >= 0.67:
        return "High"
    if ratio >= 0.34:
        return "Medium"
    return "Low"


def _research_score(text: str, item: Item) -> tuple[int, dict[str, int], dict[str, str]]:
    components = {
        "topical_fit": _component_score(text, AI_ML_TERMS, 25, 4),
        "evidence": _component_score(text, EVIDENCE_TERMS, 20, 4),
        "applicability": _component_score(text, APPLICABILITY_TERMS, 20, 4),
        "reproducibility": _component_score(text, REPRODUCIBILITY_TERMS, 15, 3),
        "novelty": _component_score(text, NOVELTY_TERMS, 10, 2),
        "recency": _recency_score(item),
    }
    signals = {
        "evidence": _signal_level(components["evidence"], 20),
        "applicability": _signal_level(components["applicability"], 20),
        "reproducibility": _signal_level(components["reproducibility"], 15),
        "novelty": _signal_level(components["novelty"], 10),
    }
    return sum(components.values()), components, signals


def _action_priority(text: str, research_signals: dict[str, str]) -> str:
    if _matches(text, SHARE_TERMS):
        return "SHARE"
    if research_signals["reproducibility"] == "High" or _matches(text, APPLICABILITY_TERMS) >= 2:
        return "EXPERIMENT"
    if _matches(text, WATCH_TERMS):
        return "WATCH"
    return "READ"


def _action_title(priority: str) -> str:
    titles = {
        "READ": "Read for research signal",
        "EXPERIMENT": "Prototype a quick evaluation",
        "SHARE": "Share for broader review",
        "WATCH": "Track for follow-up evidence",
    }
    return titles[priority]


def _paper_tags(domain: str, capability: str) -> list[str]:
    return [capability, domain]


def _has_code(text: str, item: Item) -> bool:
    related = " ".join(item.related_links).lower()
    return (
        "github" in text
        or "github" in related
        or "code" in text
        or "open-source" in text
        or "open source" in text
        or "implementation" in text
    )


def _paper_signal_id(item: Item, capability: str, domain: str) -> str:
    seed = "|".join([item.id, item.title, capability, domain])
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def enrich_paper_item(item: Item) -> Item:
    """Attach generic deterministic research metadata to a paper item."""
    text = _paper_text(item)
    capability = _best_label(text, CAPABILITY_KEYWORDS, "Other AI/ML")
    domain = _best_label(text, DOMAIN_KEYWORDS, "Other", min_score=3, reject_ties=True)
    research_score, score_components, research_signals = _research_score(text, item)
    priority = _action_priority(text, research_signals)
    action_title = _action_title(priority)
    has_code = _has_code(text, item)

    takeaways = [
        f"Focuses on {capability.lower()} with potential use in {domain.lower()}.",
        f"Action signal: {action_title.lower()} before adding it to a roadmap.",
        "Review evidence quality, datasets, and deployment assumptions before adoption.",
    ]
    if has_code:
        takeaways[2] = "Check the implementation or replication path before piloting."

    action_items = [
        f"Review {item.title} and flag the core method, evidence, and assumptions for the research brief.",
        f"Run a small evaluation to test whether {capability.lower()} improves a relevant {domain.lower()} workflow.",
        "Ask what adoption risk, data constraint, or governance question would block a responsible pilot.",
    ]

    metadata = dict(item.metadata)
    metadata.update(
        {
            "item_kind": "paper",
            "paper_signal_id": _paper_signal_id(item, capability, domain),
            "capability": capability,
            "domain": domain,
            "priority": priority,
            "action_title": action_title,
            "action_items": action_items,
            "takeaways": takeaways,
            "paper_tags": _paper_tags(domain, capability),
            "research_score": research_score,
            "research_score_components": score_components,
            "research_signals": research_signals,
            "has_code": has_code,
        }
    )
    item.metadata = metadata
    return item


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


def _pace_arxiv_request() -> None:
    """Respect arXiv's request spacing recommendation across category calls."""
    global _LAST_ARXIV_REQUEST_AT

    if _LAST_ARXIV_REQUEST_AT is not None:
        elapsed = time.monotonic() - _LAST_ARXIV_REQUEST_AT
        if elapsed < ARXIV_REQUEST_INTERVAL_SECONDS:
            time.sleep(ARXIV_REQUEST_INTERVAL_SECONDS - elapsed)
    _LAST_ARXIV_REQUEST_AT = time.monotonic()


def _retryable_arxiv_error(exc: Exception) -> bool:
    if isinstance(exc, ET.ParseError):
        return True
    if not isinstance(exc, requests.RequestException):
        return False
    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return True
    status = exc.response.status_code
    return status in ARXIV_RETRYABLE_STATUS_CODES or status >= 500


def _fetch_arxiv_category(category: str, diagnostics: dict[str, Any]) -> list[ET.Element]:
    params = {
        "search_query": f"cat:{category}",
        "start": 0,
        "max_results": ARXIV_MAX_RESULTS_PER_CATEGORY,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API_URL}?{urlencode(params)}"

    def fetch() -> list[ET.Element]:
        _pace_arxiv_request()
        diagnostics["request_attempts"] += 1
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        return root.findall("atom:entry", namespaces=ATOM_NS)

    def record_retry(exc: Exception, retry_number: int, delay: float) -> None:
        diagnostics["retry_count"] += 1
        LOGGER.warning(
            "Retrying arXiv category %s after attempt %d in %.2fs: %s",
            category,
            retry_number,
            delay,
            exc,
        )

    return retry_with_exponential_backoff(
        fetch,
        max_retries=ARXIV_MAX_RETRIES,
        retry_on=_retryable_arxiv_error,
        on_retry=record_retry,
    )


def _fetch_arxiv_entries(state: PaperGraphState) -> PaperGraphState:
    cutoff = window_start()
    fallback_cutoff = datetime.now(timezone.utc) - timedelta(days=ARXIV_FALLBACK_WINDOW_DAYS)
    primary_items: list[Item] = []
    fallback_items: list[Item] = []
    diagnostics: dict[str, Any] = {
        "categories": [],
        "raw_count": 0,
        "seven_day_count": 0,
        "fourteen_day_count": 0,
        "backfill_count": 0,
        "selected_window_days": 7,
        "deduplicated_count": 0,
        "displayed_count": 0,
        "request_attempts": 0,
        "retry_count": 0,
    }

    for category in state.get("categories", []):
        LOGGER.info("Fetching arXiv category %s", category)
        category_diagnostics = {
            "category": category,
            "status": "ok",
            "raw_count": 0,
            "seven_day_count": 0,
            "fourteen_day_count": 0,
            "request_attempts": 0,
            "retry_count": 0,
        }
        try:
            entries = _fetch_arxiv_category(category, category_diagnostics)
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
        diagnostics["request_attempts"] += category_diagnostics["request_attempts"]
        diagnostics["retry_count"] += category_diagnostics["retry_count"]
        diagnostics["categories"].append(category_diagnostics)

    return {
        **state,
        "primary_items": primary_items,
        "fallback_items": fallback_items,
        "diagnostics": diagnostics,
    }


def _select_recent_papers(state: PaperGraphState) -> PaperGraphState:
    diagnostics = dict(state.get("diagnostics", {}))
    selected: dict[str, Item] = {}
    for item in state.get("primary_items", []):
        selected.setdefault(item.url, item)
    if len(selected) < 8:
        diagnostics["selected_window_days"] = ARXIV_FALLBACK_WINDOW_DAYS
        for item in state.get("fallback_items", []):
            if item.url not in selected:
                selected[item.url] = item
                diagnostics["backfill_count"] = diagnostics.get("backfill_count", 0) + 1
            if len(selected) >= 8:
                break
    return {**state, "selected": list(selected.values()), "diagnostics": diagnostics}


def _extract_action_metadata(state: PaperGraphState) -> PaperGraphState:
    return {**state, "enriched": [enrich_paper_item(item) for item in state.get("selected", [])]}


def _run_sequential_graph(state: PaperGraphState) -> PaperGraphState:
    state = _fetch_arxiv_entries(state)
    state = _select_recent_papers(state)
    return _extract_action_metadata(state)


def fetch_papers_with_graph(categories: list[str]) -> tuple[list[Item], dict[str, Any]]:
    """Fetch, select, and enrich papers through the LangGraph workflow."""
    initial_state: PaperGraphState = {"categories": categories}
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        LOGGER.warning("langgraph is not installed; running paper workflow sequentially")
        result = _run_sequential_graph(initial_state)
        return result.get("enriched", []), result.get("diagnostics", {})

    graph = StateGraph(PaperGraphState)
    graph.add_node("fetch_arxiv_entries", _fetch_arxiv_entries)
    graph.add_node("select_recent_papers", _select_recent_papers)
    graph.add_node("extract_action_metadata", _extract_action_metadata)
    graph.set_entry_point("fetch_arxiv_entries")
    graph.add_edge("fetch_arxiv_entries", "select_recent_papers")
    graph.add_edge("select_recent_papers", "extract_action_metadata")
    graph.add_edge("extract_action_metadata", END)

    result: dict[str, Any] = graph.compile().invoke(initial_state)
    return result.get("enriched", []), result.get("diagnostics", {})
