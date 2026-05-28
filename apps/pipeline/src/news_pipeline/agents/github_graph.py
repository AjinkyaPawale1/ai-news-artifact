"""LangGraph workflow for discovering high-traction AI/LLM GitHub repos."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
from datetime import datetime, timezone
from typing import Any, TypedDict
from urllib.parse import quote_plus

import requests

from ..config import (
    CORE_AI_KEYWORDS,
    DATE_WINDOW_DAYS,
    EMERGING_AI_KEYWORDS,
    FRAMEWORK_KEYWORDS,
    GITHUB_MAX_REPO_AGE_DAYS,
    GITHUB_REPOS_EMERGING_WATCH,
    GITHUB_REPOS_EVERGREEN,
    GITHUB_SEARCH_PER_QUERY,
    GITHUB_SEARCH_QUERIES,
    MAX_ITEMS_PER_SOURCE,
    OPENAI_REPO_BRIEF_LIMIT,
    TRACTION_THRESHOLD_DEFAULT,
    TRACTION_THRESHOLD_EMERGING,
    github_repo_created_after,
    window_start,
)
from ..schema import Item, utc_now_iso

LOGGER = logging.getLogger(__name__)
GITHUB_API_URL = "https://api.github.com"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
README_CHARS = 5000
_OPENAI_ATTEMPTS = 0
_OPENAI_DISABLED_FOR_RUN = False


class GitHubGraphState(TypedDict, total=False):
    queries: list[str]
    repos_evergreen: list[str]
    repos_emerging_watch: list[str]
    dynamic_config: dict[str, Any]
    candidates: list[dict[str, Any]]
    search_diagnostics: dict[str, Any]
    enriched: list[dict[str, Any]]
    selected: list[dict[str, Any]]
    items: list[Item]


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_json(url: str) -> dict[str, Any] | list[dict[str, Any]]:
    LOGGER.info("Fetching GitHub URL %s", url)
    response = requests.get(url, headers=_github_headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def _safe_fetch_json(url: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    try:
        return _fetch_json(url)
    except requests.RequestException as exc:
        LOGGER.warning("GitHub request failed for %s: %s", url, exc)
        return None


def _parse_github_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_since(value: str) -> int | None:
    parsed = _parse_github_date(value)
    if not parsed:
        return None
    return max(0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).days)


def _format_count(value: int | None) -> str:
    value = value or 0
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _repo_key(repo: dict[str, Any]) -> str:
    return repo.get("full_name") or repo.get("html_url") or repo.get("name") or ""


def _readme_excerpt(owner_repo: str) -> str:
    data = _safe_fetch_json(f"{GITHUB_API_URL}/repos/{owner_repo}/readme")
    if not isinstance(data, dict):
        return ""
    content = data.get("content")
    if not content:
        return ""
    try:
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
    except (ValueError, TypeError):
        return ""
    return " ".join(decoded.split())[:README_CHARS]


def _latest_release(owner_repo: str) -> dict[str, Any] | None:
    data = _safe_fetch_json(f"{GITHUB_API_URL}/repos/{owner_repo}/releases/latest")
    if isinstance(data, dict) and data.get("html_url"):
        return data
    return None


def _repo_score(repo: dict[str, Any]) -> int:
    stars = int(repo.get("stargazers_count") or 0)
    forks = int(repo.get("forks_count") or 0)
    issues = int(repo.get("open_issues_count") or 0)
    topics = [str(topic).lower() for topic in repo.get("topics") or []]
    text = " ".join(
        [
            repo.get("full_name") or "",
            repo.get("description") or "",
            " ".join(topics),
            repo.get("readme_excerpt") or "",
        ]
    ).lower()

    star_score = min(int(math.log10(max(stars, 1)) * 5), 24)
    fork_score = min(int(math.log10(max(forks, 1)) * 3), 10)
    recency_days = _days_since(repo.get("pushed_at") or "")
    recency = 20 if recency_days is not None and recency_days <= 7 else 10 if recency_days is not None and recency_days <= 30 else 0
    created_days = _days_since(repo.get("created_at") or "")
    novelty = 18 if created_days is not None and created_days <= 30 else 12 if created_days is not None and created_days <= 90 else 0

    # Phase 2: tiered keyword scoring
    core_hits = sum(1 for kw in CORE_AI_KEYWORDS if kw in text)
    emerging_hits = sum(1 for kw in EMERGING_AI_KEYWORDS if kw in text)
    framework_hits = sum(1 for kw in FRAMEWORK_KEYWORDS if kw in text)
    relevance = min(core_hits * 5 + emerging_hits * 8 + framework_hits * 3, 40)
    emerging_bonus = 10 if emerging_hits >= 2 else 5 if emerging_hits >= 1 else 0

    release_bonus = 8 if repo.get("latest_release") else 0
    activity = 5 if issues > 0 else 0
    penalties = 0
    if repo.get("archived"):
        penalties += 35
    if repo.get("fork"):
        penalties += 15

    raw = star_score + fork_score + recency + novelty + relevance + emerging_bonus + release_bonus + activity - penalties
    # Tag whether this repo qualifies as an emerging-topic repo for tiered selection
    repo["_emerging_hit"] = emerging_hits > 0
    return max(0, min(110, raw))


def _repo_text(repo: dict[str, Any]) -> str:
    topics = repo.get("topics") or []
    return " ".join(
        [
            repo.get("full_name") or "",
            repo.get("description") or "",
            " ".join(str(topic) for topic in topics),
            repo.get("readme_excerpt") or "",
        ]
    ).lower()


def _best_for_label(repo: dict[str, Any]) -> str:
    text = _repo_text(repo)
    categories = [
        ("Agent Security", ["security", "cyber", "threat", "malware", "incident", "red-team", "penetration", "mitre"]),
        ("RAG Infrastructure", ["rag", "retrieval", "vector", "embedding", "knowledge base", "knowledge-base", "context"]),
        ("Coding Workflow", ["code", "coding", "review", "developer", "devtools", "github copilot", "cursor", "claude code"]),
        ("MCP Tooling", ["mcp", "model context protocol", "mcp-server", "tool server"]),
        ("AI Agent Apps", ["agent", "agents", "multiagent", "workflow", "automation", "skills"]),
        ("Model Serving", ["inference", "serving", "vllm", "serverless", "gpu", "deployment"]),
        ("AI Research", ["research", "benchmark", "evaluation", "eval", "paper", "experiment"]),
        ("Data Extraction", ["ocr", "scrape", "scraping", "extract", "document", "pdf", "crawler"]),
        ("Memory & Reasoning", ["memory", "long-term memory", "episodic memory", "reasoning", "recursive reasoning", "long-context", "context-window", "rlm", "loop-synthesis", "self-improvement"]),
    ]
    scores = [
        (label, sum(1 for keyword in keywords if keyword in text))
        for label, keywords in categories
    ]
    label, score = max(scores, key=lambda item: item[1])
    return label if score > 0 else "AI Engineering"


def _fallback_bullets(repo: dict[str, Any]) -> list[str]:
    description = (repo.get("description") or "Open-source AI repository.").rstrip(".")
    language = repo.get("language") or "multi-language"
    topics = repo.get("topics") or []
    release = repo.get("latest_release") or {}
    bullets = [
        description + ".",
        f"Primarily {language}, with topics such as {', '.join(topics[:3]) or 'AI engineering'}.",
    ]
    if release.get("tag_name"):
        bullets.append(f"Latest release {release.get('tag_name')} signals active maintenance.")
    else:
        pushed = repo.get("pushed_at") or "recent GitHub activity"
        bullets.append(f"Recent activity tracked from {pushed[:10]}.")
    return bullets[:3]


def _openai_repo_brief(repo: dict[str, Any]) -> dict[str, Any] | None:
    global _OPENAI_ATTEMPTS, _OPENAI_DISABLED_FOR_RUN  # noqa: PLW0603 - run-level API backoff state

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or _OPENAI_DISABLED_FOR_RUN or _OPENAI_ATTEMPTS >= OPENAI_REPO_BRIEF_LIMIT:
        return None
    _OPENAI_ATTEMPTS += 1

    prompt = {
        "repo": repo.get("full_name"),
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics") or [],
        "stars": repo.get("stargazers_count"),
        "pushed_at": repo.get("pushed_at"),
        "latest_release": (repo.get("latest_release") or {}).get("tag_name"),
        "readme_excerpt": repo.get("readme_excerpt", "")[:2500],
    }
    body = {
        "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "input": [
            {
                "role": "system",
                "content": (
                    "You summarize GitHub repositories for an AI/LLM intelligence brief. "
                    "Return compact JSON only with keys desc, bullets, whyTrending. "
                    "bullets must be exactly three short strings."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
        "text": {"format": {"type": "json_object"}},
    }
    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("output_text") or ""
        if not text:
            chunks = []
            for output in payload.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        chunks.append(content.get("text", ""))
            text = "".join(chunks)
        parsed = json.loads(text)
    except (requests.RequestException, json.JSONDecodeError, TypeError, KeyError) as exc:
        if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in {401, 403, 429}:
            _OPENAI_DISABLED_FOR_RUN = True
        LOGGER.warning("OpenAI repo brief failed for %s: %s", repo.get("full_name"), exc)
        return None

    bullets = [str(item).strip() for item in parsed.get("bullets", []) if str(item).strip()]
    if len(bullets) != 3:
        return None
    return {
        "desc": str(parsed.get("desc") or repo.get("description") or "").strip(),
        "bullets": bullets,
        "why_trending": str(parsed.get("whyTrending") or "").strip(),
    }


def _search_repositories(state: GitHubGraphState) -> GitHubGraphState:
    pushed_cutoff = window_start().astimezone(timezone.utc).strftime("%Y-%m-%d")
    created_cutoff = github_repo_created_after().astimezone(timezone.utc).strftime("%Y-%m-%d")
    queries = state.get("queries", GITHUB_SEARCH_QUERIES)
    repos_evergreen = state.get("repos_evergreen", GITHUB_REPOS_EVERGREEN)
    repos_emerging_watch = state.get("repos_emerging_watch", GITHUB_REPOS_EMERGING_WATCH)
    candidates: dict[str, dict[str, Any]] = {}
    diagnostics: dict[str, Any] = {
        "queries": [],
        "watch_repos": [],
        "pushed_cutoff": pushed_cutoff,
        "created_cutoff": created_cutoff,
    }
    if state.get("dynamic_config"):
        diagnostics["dynamic_config"] = state["dynamic_config"]

    for query in queries:
        before_count = len(candidates)
        encoded = quote_plus(f"{query} pushed:>={pushed_cutoff} created:>={created_cutoff}")
        data = _safe_fetch_json(
            f"{GITHUB_API_URL}/search/repositories?q={encoded}&sort=stars&order=desc&per_page={GITHUB_SEARCH_PER_QUERY}"
        )
        if not isinstance(data, dict):
            diagnostics["queries"].append(
                {
                    "query": query,
                    "fetched": 0,
                    "added": 0,
                    "failed": True,
                }
            )
            continue
        fetched = 0
        for repo in data.get("items", []):
            if isinstance(repo, dict):
                fetched += 1
                candidates[_repo_key(repo)] = repo
        diagnostics["queries"].append(
            {
                "query": query,
                "fetched": fetched,
                "added": len(candidates) - before_count,
                "failed": False,
            }
        )

    for owner_repo in repos_evergreen:
        before_count = len(candidates)
        data = _safe_fetch_json(f"{GITHUB_API_URL}/repos/{owner_repo}")
        pushed = _parse_github_date(data.get("pushed_at") or "") if isinstance(data, dict) else None
        # Evergreen: bypass created_at age filter; include if pushed within the activity window
        if isinstance(data, dict) and pushed and pushed >= window_start():
            candidates[_repo_key(data)] = data
            diagnostics["watch_repos"].append(
                {"repo": owner_repo, "added": len(candidates) - before_count, "failed": False, "skipped_old": False, "kind": "evergreen"}
            )
        else:
            diagnostics["watch_repos"].append(
                {"repo": owner_repo, "added": 0, "failed": not isinstance(data, dict), "skipped_old": isinstance(data, dict), "kind": "evergreen"}
            )

    for owner_repo in repos_emerging_watch:
        before_count = len(candidates)
        data = _safe_fetch_json(f"{GITHUB_API_URL}/repos/{owner_repo}")
        created = _parse_github_date(data.get("created_at") or "") if isinstance(data, dict) else None
        # Emerging: normal age filter applies
        if isinstance(data, dict) and created and created >= github_repo_created_after():
            candidates[_repo_key(data)] = data
            diagnostics["watch_repos"].append(
                {"repo": owner_repo, "added": len(candidates) - before_count, "failed": False, "skipped_old": False, "kind": "emerging"}
            )
        else:
            diagnostics["watch_repos"].append(
                {"repo": owner_repo, "added": 0, "failed": not isinstance(data, dict), "skipped_old": isinstance(data, dict), "kind": "emerging"}
            )

    diagnostics["total_unique_candidates"] = len(candidates)
    LOGGER.info(
        "GitHub search discovered %d unique candidates across %d queries",
        diagnostics["total_unique_candidates"],
        len(queries),
    )

    return {**state, "candidates": list(candidates.values()), "search_diagnostics": diagnostics}


def _enrich_repositories(state: GitHubGraphState) -> GitHubGraphState:
    enriched: list[dict[str, Any]] = []
    for repo in state.get("candidates", []):
        owner_repo = repo.get("full_name")
        if not owner_repo:
            continue
        repo = dict(repo)
        repo["readme_excerpt"] = _readme_excerpt(owner_repo)
        repo["latest_release"] = _latest_release(owner_repo)
        repo["traction_score"] = _repo_score(repo)
        enriched.append(repo)
    return {**state, "enriched": enriched}


def _select_repositories(state: GitHubGraphState) -> GitHubGraphState:
    created_cutoff = github_repo_created_after()
    repos = [
        repo
        for repo in state.get("enriched", [])
        if (
            repo.get("traction_score", 0) >= (
                TRACTION_THRESHOLD_EMERGING if repo.get("_emerging_hit") else TRACTION_THRESHOLD_DEFAULT
            )
        )
        and not repo.get("archived")
        and (_parse_github_date(repo.get("created_at") or "") or datetime.min.replace(tzinfo=timezone.utc)) >= created_cutoff
    ]
    repos.sort(key=lambda repo: (repo.get("traction_score", 0), repo.get("stargazers_count", 0)), reverse=True)
    return {**state, "selected": repos[:MAX_ITEMS_PER_SOURCE]}


def _repo_to_item(repo: dict[str, Any]) -> Item:
    owner_repo = repo.get("full_name", "unknown/repo")
    url = repo.get("html_url") or f"https://github.com/{owner_repo}"
    brief = _openai_repo_brief(repo)
    bullets = brief["bullets"] if brief else _fallback_bullets(repo)
    description = (brief or {}).get("desc") or repo.get("description") or bullets[0]
    why_trending = (brief or {}).get("why_trending") or (
        f"Created within {GITHUB_MAX_REPO_AGE_DAYS} days and active in the last {DATE_WINDOW_DAYS} days; "
        f"traction score {repo.get('traction_score', 0)} from stars, activity, releases, and AI topic overlap."
    )
    release = repo.get("latest_release") or {}

    return Item(
        id=f"github-{_stable_id(url)}",
        source="GitHub",
        source_type="github",
        title=owner_repo,
        url=url,
        authors=[repo.get("owner", {}).get("login", "Unknown")],
        published_date=repo.get("pushed_at") or repo.get("updated_at") or repo.get("created_at") or "",
        fetched_date=utc_now_iso(),
        raw_content=description,
        tags=repo.get("topics") or [],
        related_links=[release.get("html_url")] if release.get("html_url") else [],
        metadata={
            "item_kind": "repo",
            "stars": repo.get("stargazers_count") or 0,
            "forks": repo.get("forks_count") or 0,
            "watchers": repo.get("watchers_count") or 0,
            "open_issues": repo.get("open_issues_count") or 0,
            "language": repo.get("language") or "",
            "homepage": repo.get("homepage") or "",
            "license": (repo.get("license") or {}).get("spdx_id") or "",
            "created_at": repo.get("created_at") or "",
            "updated_at": repo.get("updated_at") or "",
            "pushed_at": repo.get("pushed_at") or "",
            "fetched_at": utc_now_iso(),
            "trend_window_days": DATE_WINDOW_DAYS,
            "max_repo_age_days": GITHUB_MAX_REPO_AGE_DAYS,
            "latest_release": release.get("tag_name") or "",
            "latest_release_url": release.get("html_url") or "",
            "best_for": _best_for_label(repo),
            "traction_score": repo.get("traction_score", 0),
            "delta": f"{repo.get('traction_score', 0)} pts",
            "bullets": bullets,
            "why_trending": why_trending,
        },
    )


def _build_items(state: GitHubGraphState) -> GitHubGraphState:
    return {**state, "items": [_repo_to_item(repo) for repo in state.get("selected", [])]}


def _run_sequential_graph(state: GitHubGraphState) -> GitHubGraphState:
    for node in (_search_repositories, _enrich_repositories, _select_repositories, _build_items):
        state = node(state)
    return state


def fetch_github_with_graph(
    *,
    queries: list[str] | None = None,
    repos_evergreen: list[str] | None = None,
    repos_emerging_watch: list[str] | None = None,
    dynamic_config: dict[str, Any] | None = None,
) -> tuple[list[Item], dict]:
    """Run the GitHub discovery workflow and return (items, diagnostics)."""
    initial_state: GitHubGraphState = {
        "queries": queries or GITHUB_SEARCH_QUERIES,
        "repos_evergreen": repos_evergreen or GITHUB_REPOS_EVERGREEN,
        "repos_emerging_watch": repos_emerging_watch or GITHUB_REPOS_EMERGING_WATCH,
    }
    if dynamic_config:
        initial_state["dynamic_config"] = dynamic_config
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        LOGGER.warning("langgraph is not installed; running GitHub workflow sequentially")
        result = _run_sequential_graph(initial_state)
        diagnostics = result.get("search_diagnostics") or {}
        if diagnostics:
            LOGGER.info("GitHub search diagnostics: %s", json.dumps(diagnostics, ensure_ascii=True))
        return result.get("items", []), diagnostics

    graph = StateGraph(GitHubGraphState)
    graph.add_node("search_repositories", _search_repositories)
    graph.add_node("enrich_repositories", _enrich_repositories)
    graph.add_node("select_repositories", _select_repositories)
    graph.add_node("build_items", _build_items)
    graph.set_entry_point("search_repositories")
    graph.add_edge("search_repositories", "enrich_repositories")
    graph.add_edge("enrich_repositories", "select_repositories")
    graph.add_edge("select_repositories", "build_items")
    graph.add_edge("build_items", END)

    result = graph.compile().invoke(initial_state)
    diagnostics = result.get("search_diagnostics") or {}
    if diagnostics:
        LOGGER.info("GitHub search diagnostics: %s", json.dumps(diagnostics, ensure_ascii=True))
    return result.get("items", []), diagnostics
