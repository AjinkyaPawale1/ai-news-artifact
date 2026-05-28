"""GitHub repository extraction agent."""

from __future__ import annotations

import logging

from ..schema import Item
from .github_dynamic import resolve_dynamic_github_inputs
from .github_graph import fetch_github_with_graph

LOGGER = logging.getLogger(__name__)

_last_diagnostics: dict | None = None


def get_last_diagnostics() -> dict | None:
    """Return the diagnostics dict from the most recent fetch_github() call."""
    return _last_diagnostics


def fetch_github() -> list[Item]:
    """Fetch high-traction GitHub repositories relevant to LLM/agent work."""
    global _last_diagnostics  # noqa: PLW0603
    resolved = resolve_dynamic_github_inputs()
    items, diagnostics = fetch_github_with_graph(
        queries=resolved.get("queries"),
        repos_evergreen=resolved.get("repos_evergreen"),
        repos_emerging_watch=resolved.get("repos_emerging_watch"),
        dynamic_config=resolved.get("dynamic_config"),
    )
    if resolved.get("dynamic_config"):
        diagnostics["dynamic_refresh"] = resolved["dynamic_config"]
    _last_diagnostics = diagnostics
    return items


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in fetch_github():
        print(item.to_dict())
