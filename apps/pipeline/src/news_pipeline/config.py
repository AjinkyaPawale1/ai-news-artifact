"""Configuration for the multi-agent news pipeline."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")

DATE_WINDOW_DAYS = int(os.getenv("DATE_WINDOW_DAYS", "7"))
MAX_ITEMS_PER_SOURCE = int(os.getenv("MAX_ITEMS_PER_SOURCE", "20"))
GITHUB_MAX_REPO_AGE_DAYS = int(os.getenv("GITHUB_MAX_REPO_AGE_DAYS", "60"))
OPENAI_REPO_BRIEF_LIMIT = int(os.getenv("OPENAI_REPO_BRIEF_LIMIT", "8"))
GITHUB_SEARCH_PER_QUERY = int(os.getenv("GITHUB_SEARCH_PER_QUERY", "8"))
GITHUB_ENABLE_EMERGING_QUERIES = os.getenv("GITHUB_ENABLE_EMERGING_QUERIES", "1").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
GITHUB_DYNAMIC_AUTO_UPDATE = os.getenv("GITHUB_DYNAMIC_AUTO_UPDATE", "1").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS = int(os.getenv("GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS", "4"))
GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS = int(os.getenv("GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS", "4"))
GITHUB_DYNAMIC_MAX_EMERGING_QUERIES = int(os.getenv("GITHUB_DYNAMIC_MAX_EMERGING_QUERIES", "7"))
GITHUB_DYNAMIC_MAX_EMERGING_WATCH = int(os.getenv("GITHUB_DYNAMIC_MAX_EMERGING_WATCH", "8"))

ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
ARXIV_MAX_RESULTS_PER_CATEGORY = int(os.getenv("ARXIV_MAX_RESULTS_PER_CATEGORY", "25"))

GITHUB_CORE_SEARCH_QUERIES = [
    "topic:llm language:python",
    "topic:agents language:python",
    "topic:rag language:python",
    "topic:generative-ai language:python",
]
GITHUB_EMERGING_SEARCH_QUERIES = [
    "reasoning language:python stars:>30",
    "memory llm language:python stars:>20",
    '"recursive language model" OR rlm language:python stars:>10',
    '"llm wiki" OR "ai wiki" stars:>5',
    "topic:model-context-protocol stars:>10",
    "topic:mcp language:python stars:>10",
    "language:typescript topic:ai stars:>20",
]
GITHUB_SEARCH_QUERIES = (
    GITHUB_CORE_SEARCH_QUERIES + GITHUB_EMERGING_SEARCH_QUERIES
    if GITHUB_ENABLE_EMERGING_QUERIES
    else GITHUB_CORE_SEARCH_QUERIES
)

# Evergreen repos: established ecosystem anchors — age filter bypassed so they
# always appear if they were recently active (pushed within DATE_WINDOW_DAYS).
GITHUB_REPOS_EVERGREEN = [
    "openai/openai-python",
    "anthropics/anthropic-sdk-python",
    "anthropics/anthropic-cookbook",
    "langchain-ai/langchain",
    "run-llama/llama_index",
    "microsoft/autogen",
    "crewAIInc/crewAI",
]
GITHUB_REPOS_EVERGREEN += [
    repo.strip()
    for repo in os.getenv("GITHUB_REPOS_EVERGREEN_EXTRA", "").split(",")
    if repo.strip()
]

# Emerging repos: newly relevant projects — subject to the normal age filter.
GITHUB_REPOS_EMERGING_WATCH = [
    "MemPalace/mempalace",
    "swarmclawai/swarmvault",
]
GITHUB_REPOS_EMERGING_WATCH += [
    repo.strip()
    for repo in os.getenv("GITHUB_REPOS_TO_WATCH_EXTRA", "").split(",")
    if repo.strip()
]

# Combined list used by the graph (kept for back-compat; graph reads both lists separately)
GITHUB_REPOS_TO_WATCH = GITHUB_REPOS_EVERGREEN + GITHUB_REPOS_EMERGING_WATCH

RSS_FEEDS = [
    "https://openai.com/news/rss.xml",
    "https://www.anthropic.com/news/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://research.google/blog/rss/",
    "https://www.microsoft.com/en-us/research/feed/",
]

MODEL_TOOL_FEEDS = [
    feed.strip()
    for feed in os.getenv("MODEL_TOOL_FEEDS", ",".join(RSS_FEEDS)).split(",")
    if feed.strip()
]
MODEL_TOOL_MAX_ITEMS = int(os.getenv("MODEL_TOOL_MAX_ITEMS", "8"))

DOMAIN_KEYWORDS = [
    "financial services",
    "banking",
    "insurance",
    "capital markets",
    "wealth management",
    "asset management",
    "risk",
    "compliance",
    "fraud",
    "portfolio",
    "trading",
]

AI_KEYWORDS = [
    "llm",
    "language model",
    "generative ai",
    "agent",
    "agents",
    "rag",
    "retrieval",
    "fine-tuning",
    "reasoning",
    "transformer",
    "multimodal",
    "open-source",
]

SCORING_KEYWORDS = sorted(set(DOMAIN_KEYWORDS + AI_KEYWORDS))

# Phase 2: Tiered keyword taxonomy for GitHub repo scoring
CORE_AI_KEYWORDS = [
    "llm",
    "language model",
    "agent",
    "agents",
    "agentic",
    "rag",
    "retrieval",
    "generative-ai",
    "generative ai",
    "genai",
]
EMERGING_AI_KEYWORDS = [
    "reasoning",
    "recursive reasoning",
    "memory",
    "long-term memory",
    "episodic memory",
    "long-context",
    "context-window",
    "extended-context",
    "knowledge-graph",
    "knowledge graph",
    "loop-synthesis",
    "self-improvement",
    "rlm",
    "wiki",
]
FRAMEWORK_KEYWORDS = [
    "langchain",
    "langgraph",
    "llamaindex",
    "model-context-protocol",
    "mcp",
    "autogen",
    "crewai",
]

# Tiered traction thresholds: lower bar for emerging-topic repos
TRACTION_THRESHOLD_DEFAULT = int(os.getenv("TRACTION_THRESHOLD_DEFAULT", "35"))
TRACTION_THRESHOLD_EMERGING = int(os.getenv("TRACTION_THRESHOLD_EMERGING", "25"))


def window_start() -> datetime:
    """Return the lower bound for item publication dates."""
    return datetime.now(timezone.utc) - timedelta(days=DATE_WINDOW_DAYS)


def github_repo_created_after() -> datetime:
    """Return the lower bound for newly created GitHub repositories."""
    return datetime.now(timezone.utc) - timedelta(days=GITHUB_MAX_REPO_AGE_DAYS)
