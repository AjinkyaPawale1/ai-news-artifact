"""LangGraph workflow for deterministic paper action extraction."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, TypedDict

from ..schema import Item

LOGGER = logging.getLogger(__name__)


class PaperGraphState(TypedDict, total=False):
    papers: list[Item]
    enriched: list[Item]


CAPABILITY_KEYWORDS = [
    (
        "Agentic AI",
        [
            "agent",
            "agents",
            "agentic",
            "multi-agent",
            "multiagent",
            "tool use",
            "planning",
        ],
    ),
    (
        "RAG and Knowledge",
        ["rag", "retrieval", "embedding", "vector", "knowledge graph", "knowledge base"],
    ),
    (
        "Model Evaluation",
        ["benchmark", "evaluation", "eval", "dataset", "leaderboard", "measure"],
    ),
    (
        "Reasoning Models",
        ["reasoning", "chain-of-thought", "planning", "mathematical", "logic"],
    ),
    (
        "Multimodal AI",
        ["multimodal", "vision-language", "image", "audio", "video", "vlm"],
    ),
    (
        "Model Efficiency",
        ["efficient", "compression", "quantization", "distillation", "latency"],
    ),
]

FSO_KEYWORDS = [
    ("Risk and Compliance", ["risk", "compliance", "audit", "regulation", "governance"]),
    ("Fraud and Security", ["fraud", "security", "attack", "privacy", "adversarial"]),
    ("Banking Operations", ["bank", "banking", "loan", "credit", "payment", "customer"]),
    ("Capital Markets", ["market", "trading", "portfolio", "asset", "investment"]),
    ("Insurance", ["insurance", "claim", "underwriting", "actuarial"]),
]

EXPERIMENT_TERMS = [
    "open-source",
    "code",
    "github",
    "implementation",
    "framework",
    "toolkit",
    "system",
]
SHARE_TERMS = ["risk", "compliance", "security", "privacy", "audit", "governance"]
WATCH_TERMS = ["survey", "position", "future work", "limitations", "preliminary"]


def _paper_text(item: Item) -> str:
    return " ".join([item.title, item.raw_content, " ".join(item.tags)]).lower()


def _matches(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _best_label(text: str, groups: list[tuple[str, list[str]]], fallback: str) -> str:
    scored = [(label, _matches(text, keywords)) for label, keywords in groups]
    label, score = max(scored, key=lambda pair: pair[1])
    return label if score else fallback


def _action_priority(text: str) -> str:
    if _matches(text, SHARE_TERMS) >= 2:
        return "SHARE"
    if _matches(text, EXPERIMENT_TERMS) >= 1:
        return "EXPERIMENT"
    if _matches(text, WATCH_TERMS) >= 1:
        return "WATCH"
    return "READ"


def _action_title(priority: str) -> str:
    titles = {
        "READ": "Read for research signal",
        "EXPERIMENT": "Prototype a quick evaluation",
        "SHARE": "Share with risk and governance leads",
        "WATCH": "Track for follow-up evidence",
    }
    return titles[priority]


def _relevance_for(domain: str, priority: str) -> dict[str, str]:
    if domain == "Risk and Compliance" or priority == "SHARE":
        return {"wam": "Medium", "cm": "Medium", "ins": "Medium", "risk": "High"}
    if domain == "Capital Markets":
        return {"wam": "High", "cm": "High", "ins": "Low", "risk": "Medium"}
    if domain == "Insurance":
        return {"wam": "Medium", "cm": "Low", "ins": "High", "risk": "Medium"}
    if domain == "Banking Operations":
        return {"wam": "Medium", "cm": "Medium", "ins": "Low", "risk": "Medium"}
    return {"wam": "Medium", "cm": "Medium", "ins": "Low", "risk": "Medium"}


def _verticals(domain: str, capability: str) -> list[str]:
    verticals = ["AI", "Research"]
    if domain != "Financial Services":
        verticals.append(domain)
    if capability not in verticals:
        verticals.append(capability)
    return verticals[:4]


def _has_code(text: str, item: Item) -> bool:
    related = " ".join(item.related_links).lower()
    return (
        "github" in text
        or "github" in related
        or "code" in text
        or "open-source" in text
        or "implementation" in text
    )


def _paper_signal_id(item: Item, capability: str, domain: str) -> str:
    seed = "|".join([item.id, item.title, capability, domain])
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def enrich_paper_item(item: Item) -> Item:
    """Attach deterministic action metadata to a paper item."""
    text = _paper_text(item)
    capability = _best_label(text, CAPABILITY_KEYWORDS, "AI Research")
    domain = _best_label(text, FSO_KEYWORDS, "Financial Services")
    priority = _action_priority(text)
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
        f"Assess whether {capability.lower()} improves a current {domain.lower()} workflow.",
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
            "verticals": _verticals(domain, capability),
            "relevance": _relevance_for(domain, priority),
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
    """Run the paper action extraction workflow."""
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
