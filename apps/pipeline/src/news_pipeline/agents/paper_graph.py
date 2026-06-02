"""LangGraph workflow for deterministic paper enrichment and ranking."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict

from ..schema import Item

LOGGER = logging.getLogger(__name__)


class PaperGraphState(TypedDict, total=False):
    papers: list[Item]
    enriched: list[Item]


CAPABILITY_KEYWORDS = [
    ("Agentic AI", ["agent", "agents", "agentic", "multi-agent", "multiagent", "tool use"]),
    (
        "RAG and Knowledge Systems",
        ["rag", "retrieval", "embedding", "vector", "knowledge graph", "knowledge base"],
    ),
    (
        "Foundation Models and Generative AI",
        ["llm", "language model", "foundation model", "generative ai", "diffusion", "transformer"],
    ),
    ("Reasoning and Planning", ["reasoning", "chain-of-thought", "planning", "mathematical", "logic"]),
    (
        "Evaluation and Benchmarks",
        ["benchmark", "evaluation", "eval", "leaderboard", "measure", "metric"],
    ),
    ("Multimodal AI", ["multimodal", "vision-language", "image", "audio", "video", "vlm"]),
    (
        "Training and Fine-Tuning",
        ["training", "fine-tuning", "finetuning", "alignment", "reinforcement learning", "rlhf"],
    ),
    (
        "Inference and Model Efficiency",
        ["inference", "efficient", "compression", "quantization", "distillation", "latency", "serving"],
    ),
    (
        "LLMOps and Production AI",
        ["llmops", "production", "deployment", "monitoring", "observability", "pipeline", "orchestration"],
    ),
    (
        "Safety, Alignment and Governance",
        ["safety", "alignment", "governance", "privacy", "adversarial", "security", "responsible ai"],
    ),
    ("Data and Synthetic Data", ["dataset", "data quality", "synthetic data", "data generation", "labeling"]),
    (
        "Classical ML and Predictive Modeling",
        ["machine learning", "classification", "regression", "forecasting", "clustering", "predictive"],
    ),
]

DOMAIN_KEYWORDS = [
    (
        "AI Engineering and Developer Tools",
        ["developer", "coding", "software", "toolkit", "framework", "orchestration", "pipeline"],
    ),
    (
        "Enterprise and Knowledge Work",
        ["enterprise", "knowledge work", "document", "workflow", "customer support", "productivity"],
    ),
    ("Security and Privacy", ["security", "privacy", "attack", "adversarial", "cyber"]),
    ("Healthcare and Life Sciences", ["healthcare", "medical", "clinical", "patient", "drug", "biology"]),
    ("Finance and Economics", ["finance", "financial", "bank", "market", "trading", "economic", "portfolio"]),
    ("Robotics and Autonomous Systems", ["robot", "robotics", "autonomous", "navigation", "control"]),
    ("Science and Research", ["science", "scientific", "research", "experiment", "laboratory"]),
    ("Education", ["education", "learning", "student", "teaching", "tutor"]),
    ("Media and Creative", ["media", "creative", "music", "video", "image generation", "design"]),
    ("Public Sector and Legal", ["legal", "law", "government", "public sector", "policy"]),
    ("Cross-domain", ["general-purpose", "cross-domain", "multi-domain", "generalizable"]),
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
    return sum(1 for keyword in keywords if keyword in text)


def _best_label(text: str, groups: list[tuple[str, list[str]]], fallback: str) -> str:
    scored = [(label, _matches(text, keywords)) for label, keywords in groups]
    label, score = max(scored, key=lambda pair: pair[1])
    return label if score else fallback


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
    domain = _best_label(text, DOMAIN_KEYWORDS, "Other")
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
        f"{action_title}: {item.title}",
        f"Assess whether {capability.lower()} improves a relevant {domain.lower()} workflow.",
        "Capture one pilot question and one risk question for stakeholder review.",
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


def _extract_action_metadata(state: PaperGraphState) -> PaperGraphState:
    return {**state, "enriched": [enrich_paper_item(item) for item in state.get("papers", [])]}


def _run_sequential_graph(state: PaperGraphState) -> PaperGraphState:
    return _extract_action_metadata(state)


def enrich_papers_with_graph(papers: list[Item]) -> list[Item]:
    """Run the paper enrichment workflow."""
    initial_state: PaperGraphState = {"papers": papers}
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        LOGGER.warning("langgraph is not installed; running paper workflow sequentially")
        return _run_sequential_graph(initial_state).get("enriched", [])

    graph = StateGraph(PaperGraphState)
    graph.add_node("extract_action_metadata", _extract_action_metadata)
    graph.set_entry_point("extract_action_metadata")
    graph.add_edge("extract_action_metadata", END)

    result: dict[str, Any] = graph.compile().invoke(initial_state)
    return result.get("enriched", [])
