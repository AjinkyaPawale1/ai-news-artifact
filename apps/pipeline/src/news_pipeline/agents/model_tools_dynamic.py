"""Dynamic feed and keyword rotation for model/tool release discovery."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from ..config import (
    MODEL_TOOL_CORE_FEEDS,
    MODEL_TOOL_DYNAMIC_AUTO_UPDATE,
    MODEL_TOOL_DYNAMIC_MAX_EMERGING_FEEDS,
    MODEL_TOOL_DYNAMIC_MAX_EMERGING_TERMS,
    MODEL_TOOL_DYNAMIC_MAX_FEED_REPLACEMENTS,
    MODEL_TOOL_DYNAMIC_MAX_TERM_REPLACEMENTS,
    MODEL_TOOL_EMERGING_FEEDS,
    MODEL_TOOL_FEED_CANDIDATES,
    MODEL_TOOL_SOURCE_PAGES,
)

LOGGER = logging.getLogger(__name__)
_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_DYNAMIC_CONFIG_PATH = Path(__file__).resolve().parents[5] / "data" / "model_tools_dynamic_config.json"
_TERM_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._+:/-]{1,39}$")
_LAST_LLM_ERROR: dict[str, Any] | None = None


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


def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Failed to load model/tools dynamic data from %s: %s", path, exc)
    return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _normalize_url(value: str) -> str | None:
    url = str(value).strip()
    if len(url) < 12 or len(url) > 240:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


def _sanitize_feed(value: str, allowed_feeds: set[str]) -> str | None:
    url = _normalize_url(value)
    if not url or url not in allowed_feeds:
        return None
    return url


def _sanitize_term(value: str) -> str | None:
    term = " ".join(str(value).strip().lower().split())
    if not _TERM_PATTERN.match(term):
        return None
    if not any(ch.isalpha() for ch in term):
        return None
    return term


def _sanitize_list(values: Any, sanitizer: Any, max_items: int) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        item = sanitizer(value)
        if item:
            cleaned.append(item)
    return _dedupe_keep_order(cleaned)[:max_items]


def _bounded_rotation(
    current: list[str],
    proposed: list[str],
    *,
    max_items: int,
    max_replacements: int,
) -> tuple[list[str], dict[str, Any]]:
    base = _dedupe_keep_order(current)[:max_items]
    if not base:
        return _dedupe_keep_order(proposed)[:max_items], {"replacements": 0, "added": [], "removed": []}

    proposal = [value for value in _dedupe_keep_order(proposed) if value not in base]
    result = list(base)
    added: list[str] = []
    removed: list[str] = []
    replacements = 0

    while proposal and replacements < max_replacements and result:
        candidate = proposal.pop(0)
        old = result.pop()
        result.insert(0, candidate)
        removed.append(old)
        added.append(candidate)
        replacements += 1

    return _dedupe_keep_order(result)[:max_items], {
        "replacements": replacements,
        "added": added,
        "removed": removed,
    }


def _signals_from_previous_run() -> dict[str, Any]:
    data_dir = _DYNAMIC_CONFIG_PATH.parent
    output = _load_json(data_dir / "output.json") or {}
    health = _load_json(data_dir / "health.json") or []
    signal: dict[str, Any] = {"models": [], "toolsServices": [], "model_tools_health": {}}

    if isinstance(output, dict):
        for key in ("models", "toolsServices"):
            values = output.get(key)
            if isinstance(values, list):
                signal[key] = [
                    {
                        "name": item.get("name", ""),
                        "org": item.get("org", ""),
                        "tag": item.get("tag", ""),
                    }
                    for item in values[:8]
                    if isinstance(item, dict)
                ]

    if isinstance(health, list):
        entry = next(
            (item for item in health if isinstance(item, dict) and item.get("source") == "model_tools"),
            None,
        )
        if isinstance(entry, dict):
            signal["model_tools_health"] = {
                "status": entry.get("status"),
                "item_count": entry.get("item_count"),
                "dynamic_config": entry.get("dynamic_config", {}),
            }

    return signal


def _call_llm_for_proposal(
    current_feeds: list[str],
    current_model_terms: list[str],
    current_tool_terms: list[str],
) -> dict[str, Any] | None:
    global _LAST_LLM_ERROR  # noqa: PLW0603
    _LAST_LLM_ERROR = None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _LAST_LLM_ERROR = {"code": "missing_api_key", "type": "configuration"}
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    prompt_payload = {
        "constraints": {
            "use_only_candidate_feeds": True,
            "max_emerging_feeds": MODEL_TOOL_DYNAMIC_MAX_EMERGING_FEEDS,
            "max_emerging_terms": MODEL_TOOL_DYNAMIC_MAX_EMERGING_TERMS,
            "feed_replacements_per_run": MODEL_TOOL_DYNAMIC_MAX_FEED_REPLACEMENTS,
            "term_replacements_per_run": MODEL_TOOL_DYNAMIC_MAX_TERM_REPLACEMENTS,
        },
        "protected_core_feeds": MODEL_TOOL_CORE_FEEDS,
        "candidate_feeds": MODEL_TOOL_FEED_CANDIDATES,
        "current_emerging_feeds": current_feeds,
        "current_emerging_model_terms": current_model_terms,
        "current_emerging_tool_terms": current_tool_terms,
        "recent_run_signals": _signals_from_previous_run(),
    }
    body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": (
                    "You tune an AI model/tool release discovery pipeline. "
                    "Return JSON only with keys emerging_feeds, emerging_model_terms, emerging_tool_terms. "
                    "Feeds must be copied exactly from candidate_feeds. Terms should be short product, model, "
                    "agent, developer-tool, or release-discovery terms likely to catch emerging AI launches."
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
    except requests.HTTPError as exc:
        error_payload = {}
        if exc.response is not None:
            try:
                error_payload = exc.response.json().get("error") or {}
            except (ValueError, TypeError):
                error_payload = {}
        _LAST_LLM_ERROR = {
            "code": error_payload.get("code") or "http_error",
            "type": error_payload.get("type") or "http_error",
            "status": exc.response.status_code if exc.response is not None else None,
        }
        LOGGER.warning("Dynamic model/tools proposal call failed: %s", exc)
        return None
    except (requests.RequestException, json.JSONDecodeError, TypeError, KeyError) as exc:
        _LAST_LLM_ERROR = {"code": "request_failed", "type": type(exc).__name__}
        LOGGER.warning("Dynamic model/tools proposal call failed: %s", exc)
        return None


def resolve_dynamic_model_tool_inputs() -> dict[str, Any]:
    """Resolve active feeds and emerging keyword terms for model/tool discovery."""
    allowed_feeds = set(MODEL_TOOL_FEED_CANDIDATES)
    target_feed_count = max(1, MODEL_TOOL_DYNAMIC_MAX_EMERGING_FEEDS)
    target_term_count = max(1, MODEL_TOOL_DYNAMIC_MAX_EMERGING_TERMS)
    persisted = _load_json(_DYNAMIC_CONFIG_PATH) or {}

    persisted_feeds = _sanitize_list(
        persisted.get("emerging_feeds", []) if isinstance(persisted, dict) else [],
        lambda value: _sanitize_feed(value, allowed_feeds),
        target_feed_count,
    )
    persisted_model_terms = _sanitize_list(
        persisted.get("emerging_model_terms", []) if isinstance(persisted, dict) else [],
        _sanitize_term,
        target_term_count,
    )
    persisted_tool_terms = _sanitize_list(
        persisted.get("emerging_tool_terms", []) if isinstance(persisted, dict) else [],
        _sanitize_term,
        target_term_count,
    )

    active_feeds = persisted_feeds or _sanitize_list(
        MODEL_TOOL_EMERGING_FEEDS,
        lambda value: _sanitize_feed(value, allowed_feeds),
        target_feed_count,
    )
    active_model_terms = persisted_model_terms
    active_tool_terms = persisted_tool_terms

    refresh_meta: dict[str, Any] = {
        "auto_update_enabled": MODEL_TOOL_DYNAMIC_AUTO_UPDATE,
        "used_persisted_state": bool(persisted_feeds or persisted_model_terms or persisted_tool_terms),
        "updated": False,
        "source": "persisted" if persisted_feeds or persisted_model_terms or persisted_tool_terms else "static",
    }

    proposal = None
    if MODEL_TOOL_DYNAMIC_AUTO_UPDATE:
        proposal = _call_llm_for_proposal(active_feeds, active_model_terms, active_tool_terms)

    if isinstance(proposal, dict):
        proposed_feeds = _sanitize_list(
            proposal.get("emerging_feeds", []),
            lambda value: _sanitize_feed(value, allowed_feeds),
            target_feed_count,
        )
        proposed_model_terms = _sanitize_list(
            proposal.get("emerging_model_terms", []),
            _sanitize_term,
            target_term_count,
        )
        proposed_tool_terms = _sanitize_list(
            proposal.get("emerging_tool_terms", []),
            _sanitize_term,
            target_term_count,
        )

        feed_rotation = {"replacements": 0, "added": [], "removed": []}
        model_term_rotation = {"replacements": 0, "added": [], "removed": []}
        tool_term_rotation = {"replacements": 0, "added": [], "removed": []}
        if proposed_feeds:
            active_feeds, feed_rotation = _bounded_rotation(
                active_feeds,
                proposed_feeds,
                max_items=target_feed_count,
                max_replacements=max(0, MODEL_TOOL_DYNAMIC_MAX_FEED_REPLACEMENTS),
            )
        if proposed_model_terms:
            active_model_terms, model_term_rotation = _bounded_rotation(
                active_model_terms or proposed_model_terms,
                proposed_model_terms,
                max_items=target_term_count,
                max_replacements=max(0, MODEL_TOOL_DYNAMIC_MAX_TERM_REPLACEMENTS),
            )
        if proposed_tool_terms:
            active_tool_terms, tool_term_rotation = _bounded_rotation(
                active_tool_terms or proposed_tool_terms,
                proposed_tool_terms,
                max_items=target_term_count,
                max_replacements=max(0, MODEL_TOOL_DYNAMIC_MAX_TERM_REPLACEMENTS),
            )
        refresh_meta.update(
            {
                "updated": True,
                "source": "llm",
                "feed_rotation": feed_rotation,
                "model_term_rotation": model_term_rotation,
                "tool_term_rotation": tool_term_rotation,
            }
        )
    elif MODEL_TOOL_DYNAMIC_AUTO_UPDATE:
        refresh_meta["llm_status"] = "unavailable_or_invalid"
        if _LAST_LLM_ERROR:
            refresh_meta["llm_error_code"] = _LAST_LLM_ERROR.get("code")
            refresh_meta["llm_error_type"] = _LAST_LLM_ERROR.get("type")
            refresh_meta["llm_error_status"] = _LAST_LLM_ERROR.get("status")

    payload = {
        "version": 1,
        "updated_at": _utc_now_iso(),
        "source": refresh_meta.get("source", "static"),
        "core_feeds": MODEL_TOOL_CORE_FEEDS,
        "source_pages": MODEL_TOOL_SOURCE_PAGES,
        "emerging_feeds": active_feeds,
        "emerging_model_terms": active_model_terms,
        "emerging_tool_terms": active_tool_terms,
        "refresh": refresh_meta,
    }
    _write_json(_DYNAMIC_CONFIG_PATH, payload)

    return {
        "feeds": _dedupe_keep_order([*MODEL_TOOL_CORE_FEEDS, *active_feeds]),
        "source_pages": list(MODEL_TOOL_SOURCE_PAGES),
        "emerging_model_terms": active_model_terms,
        "emerging_tool_terms": active_tool_terms,
        "dynamic_config": {
            "state_path": str(_DYNAMIC_CONFIG_PATH),
            "active_core_feeds": len(MODEL_TOOL_CORE_FEEDS),
            "active_emerging_feeds": len(active_feeds),
            "active_source_pages": len(MODEL_TOOL_SOURCE_PAGES),
            "active_emerging_model_terms": len(active_model_terms),
            "active_emerging_tool_terms": len(active_tool_terms),
            **refresh_meta,
        },
    }
