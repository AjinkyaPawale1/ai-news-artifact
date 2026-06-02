"""Optional OpenAI summaries for the displayed paper cards."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

from .config import OPENAI_PAPER_SUMMARY_LIMIT

LOGGER = logging.getLogger(__name__)
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
_OPENAI_DISABLED_FOR_RUN = False


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


def _openai_takeaways(item: dict) -> list[str] | None:
    global _OPENAI_DISABLED_FOR_RUN

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or _OPENAI_DISABLED_FOR_RUN:
        return None
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
    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=45,
        )
        response.raise_for_status()
        parsed = json.loads(_response_text(response.json()))
    except (requests.RequestException, json.JSONDecodeError, TypeError, KeyError) as exc:
        if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code in {401, 403, 429}:
            _OPENAI_DISABLED_FOR_RUN = True
        LOGGER.warning("OpenAI paper summary failed for %s: %s", item.get("title"), exc)
        return None

    bullets = [str(bullet).strip() for bullet in parsed.get("bullets", []) if str(bullet).strip()]
    return bullets if len(bullets) == 3 else None


def enrich_paper_summaries(items: list[dict]) -> list[dict]:
    """Attach exactly three summary bullets to the highest-ranked displayed papers."""
    papers = [item for item in items if item.get("source_type") == "paper"]
    papers.sort(key=lambda item: (item.get("metadata") or {}).get("research_score", 0), reverse=True)
    for item in papers[:OPENAI_PAPER_SUMMARY_LIMIT]:
        metadata = item.get("metadata") or {}
        metadata["takeaways"] = _openai_takeaways(item) or _fallback_takeaways(item)
        item["metadata"] = metadata
    return items
