"""Optional OpenAI summaries and action items for displayed paper cards."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

from .config import (
    OPENAI_PAPER_ACTION_LIMIT,
    OPENAI_PAPER_ACTION_MAX_RETRIES,
    OPENAI_PAPER_SUMMARY_LIMIT,
    OPENAI_PAPER_SUMMARY_MAX_RETRIES,
)
from .retry import retry_with_exponential_backoff

LOGGER = logging.getLogger(__name__)
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_RETRYABLE_STATUS_CODES = {408, 425, 429}
_OPENAI_DISABLED_FOR_RUN = False
_OPENAI_ACTIONS_DISABLED_FOR_RUN = False
_LAST_DIAGNOSTICS: dict[str, Any] = {}
_LAST_ACTION_DIAGNOSTICS: dict[str, Any] = {}


class PaperSummaryResponseError(ValueError):
    """Raised when an OpenAI paper summary does not match the required shape."""


class PaperActionResponseError(ValueError):
    """Raised when an OpenAI paper action response does not match the required shape."""


def _abstract_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


def _fallback_takeaways(item: dict) -> list[str]:
    """Return three abstract-grounded bullets when OpenAI is unavailable."""
    metadata = item.get("metadata") or {}
    sentences = _abstract_sentences(item.get("raw_content", ""))
    bullets = sentences[:3]
    defaults = [
        f"Focuses on {metadata.get('capability', 'AI/ML research').lower()}.",
        f"Primary application domain: {metadata.get('domain', 'other').lower()}.",
        "Review the abstract, evidence, and implementation details before adoption.",
    ]
    for default in defaults:
        if len(bullets) >= 3:
            break
        bullets.append(default)
    return bullets[:3]


def _fallback_action_items(item: dict) -> list[str]:
    """Return the deterministic three-action fallback for a paper."""
    metadata = item.get("metadata") or {}
    existing = [str(action).strip() for action in metadata.get("action_items", []) if str(action).strip()]
    if len(existing) == 3 and len(set(existing)) == 3:
        return existing
    title = item.get("title") or "this paper"
    capability = str(metadata.get("capability") or "AI/ML research").lower()
    domain = str(metadata.get("domain") or "a relevant workflow").lower()
    return [
        f"Review {title} and flag the core method, evidence, and assumptions for the research brief.",
        f"Run a small evaluation to test whether {capability} improves {domain} in a realistic workflow.",
        "Ask what adoption risk, data constraint, or governance question would block a responsible pilot.",
    ]


def _response_text(payload: dict[str, Any]) -> str:
    text = payload.get("output_text") or ""
    if text:
        return text
    chunks = []
    for output in payload.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return "".join(chunks)


def _new_diagnostics() -> dict[str, Any]:
    return {
        "attempted_papers": 0,
        "request_attempts": 0,
        "retry_count": 0,
        "successes": 0,
        "fallbacks": 0,
        "disabled": False,
        "skip_reason": "",
    }


def _openai_error_code(exc: requests.HTTPError) -> str:
    if exc.response is None:
        return ""
    try:
        payload = exc.response.json()
    except (TypeError, ValueError):
        return ""
    return str((payload.get("error") or {}).get("code") or "")


def _retryable_openai_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            json.JSONDecodeError,
            PaperSummaryResponseError,
            PaperActionResponseError,
            requests.Timeout,
            requests.ConnectionError,
        ),
    ):
        return True
    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return False
    if _openai_error_code(exc) == "insufficient_quota":
        return False
    status = exc.response.status_code
    return status in OPENAI_RETRYABLE_STATUS_CODES or status >= 500


def _disable_openai_for_run(reason: str) -> None:
    global _OPENAI_DISABLED_FOR_RUN

    _OPENAI_DISABLED_FOR_RUN = True
    _LAST_DIAGNOSTICS.update({"disabled": True, "skip_reason": reason})


def _disable_openai_actions_for_run(reason: str) -> None:
    global _OPENAI_ACTIONS_DISABLED_FOR_RUN

    _OPENAI_ACTIONS_DISABLED_FOR_RUN = True
    _LAST_ACTION_DIAGNOSTICS.update({"disabled": True, "skip_reason": reason})


def _openai_takeaways(item: dict) -> list[str] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _LAST_DIAGNOSTICS["skip_reason"] = "missing_api_key"
        return None
    if _OPENAI_DISABLED_FOR_RUN:
        return None
    _LAST_DIAGNOSTICS["attempted_papers"] += 1
    metadata = item.get("metadata") or {}
    body = {
        "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "input": [
            {
                "role": "system",
                "content": (
                    "Summarize an AI/ML research paper for a weekly intelligence dashboard. "
                    "Return JSON only with key bullets. bullets must be exactly three concise, "
                    "specific strings grounded only in the supplied title and abstract. Cover "
                    "the paper's contribution, evidence or method, and practical implication. "
                    "Do not add unsupported claims."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "title": item.get("title"),
                        "abstract": item.get("raw_content"),
                        "capability": metadata.get("capability"),
                        "domain": metadata.get("domain"),
                    },
                    ensure_ascii=True,
                ),
            },
        ],
        "text": {"format": {"type": "json_object"}},
    }

    def request_summary() -> list[str]:
        _LAST_DIAGNOSTICS["request_attempts"] += 1
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise PaperSummaryResponseError("OpenAI response payload must be an object")
        parsed = json.loads(_response_text(payload))
        if not isinstance(parsed, dict):
            raise PaperSummaryResponseError("OpenAI paper summary must be a JSON object")
        raw_bullets = parsed.get("bullets")
        if not isinstance(raw_bullets, list):
            raise PaperSummaryResponseError("OpenAI paper summary must contain a bullets array")
        bullets = [str(bullet).strip() for bullet in raw_bullets if str(bullet).strip()]
        if len(bullets) != 3:
            raise PaperSummaryResponseError("OpenAI paper summary must contain exactly three bullets")
        return bullets

    def record_retry(exc: Exception, retry_number: int, delay: float) -> None:
        _LAST_DIAGNOSTICS["retry_count"] += 1
        LOGGER.warning(
            "Retrying OpenAI paper summary for %s after attempt %d in %.2fs: %s",
            item.get("title"),
            retry_number,
            delay,
            exc,
        )

    try:
        bullets = retry_with_exponential_backoff(
            request_summary,
            max_retries=OPENAI_PAPER_SUMMARY_MAX_RETRIES,
            retry_on=_retryable_openai_error,
            on_retry=record_retry,
        )
    except (requests.RequestException, json.JSONDecodeError, PaperSummaryResponseError, TypeError, KeyError) as exc:
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            if exc.response.status_code in {401, 403}:
                _disable_openai_for_run(f"http_{exc.response.status_code}")
            elif _openai_error_code(exc) == "insufficient_quota":
                _disable_openai_for_run("insufficient_quota")
        LOGGER.warning("OpenAI paper summary failed for %s: %s", item.get("title"), exc)
        return None

    _LAST_DIAGNOSTICS["successes"] += 1
    return bullets


def _validate_actions(raw_actions: Any) -> list[str]:
    if not isinstance(raw_actions, list):
        raise PaperActionResponseError("OpenAI paper actions must contain an actions array")
    actions = [str(action).strip() for action in raw_actions if str(action).strip()]
    if len(actions) != 3:
        raise PaperActionResponseError("OpenAI paper actions must contain exactly three actions")
    if len(set(actions)) != 3:
        raise PaperActionResponseError("OpenAI paper actions must be non-repetitive")
    return actions


def _openai_action_items(item: dict) -> list[str] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _LAST_ACTION_DIAGNOSTICS["skip_reason"] = "missing_api_key"
        return None
    if _OPENAI_ACTIONS_DISABLED_FOR_RUN:
        return None
    _LAST_ACTION_DIAGNOSTICS["attempted_papers"] += 1
    metadata = item.get("metadata") or {}
    body = {
        "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "input": [
            {
                "role": "system",
                "content": (
                    "Generate action items for an AI/ML research paper dashboard. Return JSON only "
                    "with key actions. actions must be exactly three specific, grounded, "
                    "non-repetitive strings based only on the supplied title, abstract, metadata, "
                    "and takeaways. The three actions must be, in order: immediate review action; "
                    "experiment or evaluation action; risk or adoption question. Do not add "
                    "unsupported claims."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "title": item.get("title"),
                        "abstract": item.get("raw_content"),
                        "capability": metadata.get("capability"),
                        "domain": metadata.get("domain"),
                        "priority": metadata.get("priority"),
                        "research_signals": metadata.get("research_signals"),
                        "takeaways": metadata.get("takeaways"),
                    },
                    ensure_ascii=True,
                ),
            },
        ],
        "text": {"format": {"type": "json_object"}},
    }

    def request_actions() -> list[str]:
        _LAST_ACTION_DIAGNOSTICS["request_attempts"] += 1
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise PaperActionResponseError("OpenAI response payload must be an object")
        parsed = json.loads(_response_text(payload))
        if not isinstance(parsed, dict):
            raise PaperActionResponseError("OpenAI paper actions must be a JSON object")
        return _validate_actions(parsed.get("actions"))

    def record_retry(exc: Exception, retry_number: int, delay: float) -> None:
        _LAST_ACTION_DIAGNOSTICS["retry_count"] += 1
        LOGGER.warning(
            "Retrying OpenAI paper actions for %s after attempt %d in %.2fs: %s",
            item.get("title"),
            retry_number,
            delay,
            exc,
        )

    try:
        actions = retry_with_exponential_backoff(
            request_actions,
            max_retries=OPENAI_PAPER_ACTION_MAX_RETRIES,
            retry_on=_retryable_openai_error,
            on_retry=record_retry,
        )
    except (requests.RequestException, json.JSONDecodeError, PaperActionResponseError, TypeError, KeyError) as exc:
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            if exc.response.status_code in {401, 403}:
                _disable_openai_actions_for_run(f"http_{exc.response.status_code}")
            elif _openai_error_code(exc) == "insufficient_quota":
                _disable_openai_actions_for_run("insufficient_quota")
        LOGGER.warning("OpenAI paper actions failed for %s: %s", item.get("title"), exc)
        return None

    _LAST_ACTION_DIAGNOSTICS["successes"] += 1
    return actions


def get_last_summary_diagnostics() -> dict[str, Any]:
    """Return diagnostics for the latest paper-summary pass."""
    return dict(_LAST_DIAGNOSTICS)


def get_last_action_diagnostics() -> dict[str, Any]:
    """Return diagnostics for the latest paper-action pass."""
    return dict(_LAST_ACTION_DIAGNOSTICS)


def enrich_paper_summaries(items: list[dict]) -> list[dict]:
    """Attach exactly three summary bullets to the highest-ranked displayed papers."""
    global _LAST_DIAGNOSTICS, _OPENAI_DISABLED_FOR_RUN

    _OPENAI_DISABLED_FOR_RUN = False
    _LAST_DIAGNOSTICS = _new_diagnostics()
    papers = [item for item in items if item.get("source_type") == "paper"]
    papers.sort(key=lambda item: (item.get("metadata") or {}).get("research_score", 0), reverse=True)
    for item in papers[:OPENAI_PAPER_SUMMARY_LIMIT]:
        metadata = item.get("metadata") or {}
        takeaways = _openai_takeaways(item)
        if takeaways is None:
            _LAST_DIAGNOSTICS["fallbacks"] += 1
            takeaways = _fallback_takeaways(item)
        metadata["takeaways"] = takeaways
        item["metadata"] = metadata
    return items


def enrich_paper_action_items(items: list[dict]) -> list[dict]:
    """Attach exactly three action items to the highest-ranked displayed papers."""
    global _LAST_ACTION_DIAGNOSTICS, _OPENAI_ACTIONS_DISABLED_FOR_RUN

    _OPENAI_ACTIONS_DISABLED_FOR_RUN = False
    _LAST_ACTION_DIAGNOSTICS = _new_diagnostics()
    papers = [item for item in items if item.get("source_type") == "paper"]
    papers.sort(key=lambda item: (item.get("metadata") or {}).get("research_score", 0), reverse=True)
    for item in papers[:OPENAI_PAPER_ACTION_LIMIT]:
        metadata = item.get("metadata") or {}
        actions = _openai_action_items(item)
        if actions is None:
            _LAST_ACTION_DIAGNOSTICS["fallbacks"] += 1
            actions = _fallback_action_items(item)
        metadata["action_items"] = actions[:3]
        item["metadata"] = metadata
    return items
