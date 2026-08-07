"""Loader for maintainer-approved, dashboard-suggested sources.

Populated by the source-suggestion GitHub issue workflow
(.github/workflows/approve-source.yml), which commits directly to
data/user_sources.json after a maintainer applies the `source-approved`
label. Kept separate from the self-tuning dynamic config JSONs, which are
not committed by the weekly pipeline run.
"""

from __future__ import annotations

import json
from pathlib import Path

USER_SOURCES_PATH = Path(__file__).resolve().parents[4] / "data" / "user_sources.json"


def load_user_sources() -> dict:
    if not USER_SOURCES_PATH.exists():
        return {}
    try:
        data = json.loads(USER_SOURCES_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def merged(base: list[str], key: str) -> list[str]:
    """Append deduped user-submitted entries for `key` onto `base`, preserving order."""
    extra = load_user_sources().get(key, [])
    if not isinstance(extra, list):
        return list(base)
    seen = set(base)
    result = list(base)
    for entry in extra:
        if isinstance(entry, str) and entry.strip() and entry not in seen:
            result.append(entry.strip())
            seen.add(entry)
    return result
