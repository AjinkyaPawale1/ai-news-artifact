"""Dynamic rotation for GitHub emerging queries and watch repos."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from ..config import (
    GITHUB_CORE_SEARCH_QUERIES,
    GITHUB_DYNAMIC_AUTO_UPDATE,
    GITHUB_DYNAMIC_MAX_EMERGING_QUERIES,
    GITHUB_DYNAMIC_MAX_EMERGING_WATCH,
    GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS,
    GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS,
    GITHUB_EMERGING_SEARCH_QUERIES,
    GITHUB_ENABLE_EMERGING_QUERIES,
    GITHUB_REPOS_EMERGING_WATCH,
    GITHUB_REPOS_EVERGREEN,
)

LOGGER = logging.getLogger(__name__)
_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_DYNAMIC_CONFIG_PATH = Path(__file__).resolve().parents[5] / "data" / "github_dynamic_config.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe_keep_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _sanitize_query(value: str) -> str | None:
    query = " ".join(str(value).strip().split())
    if len(query) < 5 or len(query) > 140:
        return None
    if not any(ch.isalpha() for ch in query):
        return None
    return query


def _sanitize_repo(value: str) -> str | None:
    repo = str(value).strip()
    if not _REPO_PATTERN.match(repo):
        return None
    return repo


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Failed to load dynamic GitHub config from %s: %s", path, exc)
    return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _signals_from_previous_run() -> dict[str, Any]:
    output_path = _DYNAMIC_CONFIG_PATH.parent / "output.json"
    health_path = _DYNAMIC_CONFIG_PATH.parent / "health.json"
    signal: dict[str, Any] = {"repos": [], "query_stats": [], "watch_stats": []}

    output = _load_json(output_path) or {}
    repos = output.get("repos") if isinstance(output, dict) else []
    if isinstance(repos, list):
        for repo in repos[:12]:
            if not isinstance(repo, dict):
                continue
            signal["repos"].append(
                {
                    "name": repo.get("name", ""),
                    "topics": repo.get("topics", []),
                    "bestFor": repo.get("bestFor", ""),
                }
            )

    health = _load_json(health_path)
    if isinstance(health, list):
        github_entry = next(
            (entry for entry in health if isinstance(entry, dict) and entry.get("source") == "github"),
            None,
        )
        if isinstance(github_entry, dict):
            diagnostics = github_entry.get("search_diagnostics") or {}
            queries = diagnostics.get("queries") if isinstance(diagnostics, dict) else []
            watches = diagnostics.get("watch_repos") if isinstance(diagnostics, dict) else []
            if isinstance(queries, list):
                signal["query_stats"] = [q for q in queries[:20] if isinstance(q, dict)]
            if isinstance(watches, list):
                signal["watch_stats"] = [w for w in watches[:20] if isinstance(w, dict)]
    return signal


def _call_llm_for_proposal(current_queries: list[str], current_watch: list[str]) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    signal = _signals_from_previous_run()
    prompt_payload = {
        "constraints": {
            "query_replacements_per_run": GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS,
            "watch_replacements_per_run": GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS,
            "max_emerging_queries": GITHUB_DYNAMIC_MAX_EMERGING_QUERIES,
            "max_emerging_watch_repos": GITHUB_DYNAMIC_MAX_EMERGING_WATCH,
        },
        "current_emerging_queries": current_queries,
        "current_emerging_watch_repos": current_watch,
        "recent_run_signals": signal,
    }
    body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You tune GitHub discovery for AI/LLM emerging topics. "
                    "Return JSON only with keys emerging_queries and emerging_watch_repos. "
                    "Each list should be high-signal, non-duplicate, and practical for GitHub search."
                ),
            },
            {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=True)},
        ],
        "text": {"format": {"type": "json_object"}},
    }

    try:
        response = requests.post(
            _OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("output_text") or ""
        if not text:
            chunks: list[str] = []
            for output in payload.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        chunks.append(content.get("text", ""))
            text = "".join(chunks)
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (requests.RequestException, json.JSONDecodeError, TypeError, KeyError) as exc:
        LOGGER.warning("Dynamic GitHub proposal call failed: %s", exc)
        return None


def _bounded_rotation(
    current: list[str],
    proposed: list[str],
    *,
    max_items: int,
    max_replacements: int,
    protected: set[str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    protected = protected or set()
    base = _dedupe_keep_order(current)[:max_items]
    if not base:
        base = _dedupe_keep_order(proposed)[:max_items]
        return base, {"replacements": 0, "added": [], "removed": []}

    proposal = [value for value in _dedupe_keep_order(proposed) if value not in base]
    result = list(base)
    replaceable_indexes = [i for i, value in enumerate(result) if value not in protected]
    added: list[str] = []
    removed: list[str] = []

    replacements = 0
    while proposal and replaceable_indexes and replacements < max_replacements:
        candidate = proposal.pop(0)
        idx = replaceable_indexes.pop()
        old = result[idx]
        result[idx] = candidate
        removed.append(old)
        added.append(candidate)
        replacements += 1

    for pinned in protected:
        if pinned in result:
            continue
        if len(result) < max_items:
            result.insert(0, pinned)
            continue
        non_protected_idx = next((i for i, value in enumerate(result) if value not in protected), None)
        if non_protected_idx is not None:
            removed.append(result[non_protected_idx])
            result[non_protected_idx] = pinned
            added.append(pinned)

    return _dedupe_keep_order(result)[:max_items], {
        "replacements": replacements,
        "added": added,
        "removed": removed,
    }


def _sanitize_list(values: Any, sanitizer: Any, max_items: int) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        item = sanitizer(value)
        if item:
            cleaned.append(item)
    return _dedupe_keep_order(cleaned)[:max_items]


def resolve_dynamic_github_inputs() -> dict[str, Any]:
    """Resolve active GitHub query/watch inputs, optionally refreshing dynamically."""
    static_emerging_queries = list(GITHUB_EMERGING_SEARCH_QUERIES)
    static_emerging_watch = list(GITHUB_REPOS_EMERGING_WATCH)
    target_query_count = max(1, GITHUB_DYNAMIC_MAX_EMERGING_QUERIES)
    target_watch_count = max(1, GITHUB_DYNAMIC_MAX_EMERGING_WATCH)

    persisted = _load_json(_DYNAMIC_CONFIG_PATH) or {}
    persisted_queries = _sanitize_list(
        persisted.get("emerging_queries", []),
        _sanitize_query,
        target_query_count,
    )
    persisted_watch = _sanitize_list(
        persisted.get("emerging_watch_repos", []),
        _sanitize_repo,
        target_watch_count,
    )

    active_queries = persisted_queries or static_emerging_queries[:target_query_count]
    active_watch = persisted_watch or static_emerging_watch[:target_watch_count]

    refresh_meta: dict[str, Any] = {
        "auto_update_enabled": GITHUB_DYNAMIC_AUTO_UPDATE,
        "used_persisted_state": bool(persisted_queries or persisted_watch),
        "updated": False,
        "source": "persisted" if (persisted_queries or persisted_watch) else "static",
    }

    proposal = None
    if GITHUB_DYNAMIC_AUTO_UPDATE:
        proposal = _call_llm_for_proposal(active_queries, active_watch)

    if isinstance(proposal, dict):
        proposed_queries = _sanitize_list(
            proposal.get("emerging_queries", []),
            _sanitize_query,
            target_query_count,
        )
        proposed_watch = _sanitize_list(
            proposal.get("emerging_watch_repos", []),
            _sanitize_repo,
            target_watch_count,
        )

        if proposed_queries:
            active_queries, query_rotation = _bounded_rotation(
                active_queries,
                proposed_queries,
                max_items=target_query_count,
                max_replacements=max(0, GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS),
            )
        else:
            query_rotation = {"replacements": 0, "added": [], "removed": []}

        if proposed_watch:
            active_watch, watch_rotation = _bounded_rotation(
                active_watch,
                proposed_watch,
                max_items=target_watch_count,
                max_replacements=max(0, GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS),
            )
        else:
            watch_rotation = {"replacements": 0, "added": [], "removed": []}

        refresh_meta.update(
            {
                "updated": True,
                "source": "llm",
                "query_rotation": query_rotation,
                "watch_rotation": watch_rotation,
            }
        )
    else:
        refresh_meta["source"] = "persisted" if (persisted_queries or persisted_watch) else "static"
        if GITHUB_DYNAMIC_AUTO_UPDATE:
            refresh_meta["llm_status"] = "unavailable_or_invalid"

    payload = {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "source": refresh_meta.get("source", "static"),
        "emerging_queries": active_queries,
        "emerging_watch_repos": active_watch,
        "refresh": refresh_meta,
    }
    _write_json(_DYNAMIC_CONFIG_PATH, payload)

    merged_queries = (
        [*GITHUB_CORE_SEARCH_QUERIES, *active_queries]
        if GITHUB_ENABLE_EMERGING_QUERIES
        else list(GITHUB_CORE_SEARCH_QUERIES)
    )

    return {
        "queries": merged_queries,
        "repos_evergreen": list(GITHUB_REPOS_EVERGREEN),
        "repos_emerging_watch": active_watch,
        "dynamic_config": {
            "state_path": str(_DYNAMIC_CONFIG_PATH),
            "active_emerging_queries": len(active_queries),
            "active_emerging_watch_repos": len(active_watch),
            **refresh_meta,
        },
    }
