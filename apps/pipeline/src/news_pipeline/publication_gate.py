"""Validate that a generated weekly artifact is safe to publish."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .push_to_artifact import ARCHIVE_INDEX_PATH, DATA_DIR, OUTPUT_PATH

HEALTH_PATH = DATA_DIR / "health.json"
REQUIRED_SOURCES = {"papers", "github", "rss", "model_tools"}


def validate_publication(
    current: dict[str, Any],
    health: list[dict[str, Any]],
    archive_index: dict[str, Any],
    archived: dict[str, Any],
) -> list[str]:
    """Return publication-blocking validation errors."""
    errors: list[str] = []
    source_entries: dict[str, list[dict[str, Any]]] = {}
    for entry in health:
        source = entry.get("source")
        if source in REQUIRED_SOURCES:
            source_entries.setdefault(source, []).append(entry)

    for source in sorted(REQUIRED_SOURCES):
        entries = source_entries.get(source, [])
        if len(entries) != 1:
            errors.append(f"expected exactly one health entry for {source}, found {len(entries)}")
            continue
        if entries[0].get("status") != "ok":
            errors.append(f"required source {source} is not healthy")

    required_sections = {
        "papers": current.get("papers"),
        "repos": current.get("repos"),
        "blogs": current.get("blogs"),
    }
    for section, items in required_sections.items():
        if not isinstance(items, list) or not items:
            errors.append(f"current artifact has no {section}")

    releases = (current.get("models") or []) + (current.get("toolsServices") or [])
    if not releases:
        errors.append("current artifact has no model or tool/service releases")

    editions = archive_index.get("editions") if isinstance(archive_index, dict) else None
    if not isinstance(editions, list) or not editions:
        errors.append("archive index has no editions")
    elif archived.get("generatedAt") != current.get("generatedAt"):
        errors.append("latest archive does not match current output")

    return errors


def validate_publication_files(
    output_path: Path = OUTPUT_PATH,
    health_path: Path = HEALTH_PATH,
    archive_index_path: Path = ARCHIVE_INDEX_PATH,
) -> None:
    """Load generated files and raise when the weekly edition is incomplete."""
    current = json.loads(output_path.read_text(encoding="utf-8"))
    health = json.loads(health_path.read_text(encoding="utf-8"))
    archive_index = json.loads(archive_index_path.read_text(encoding="utf-8"))
    editions = archive_index.get("editions") or []
    archived = {}
    if editions:
        archived_path = DATA_DIR / editions[0]["outputPath"]
        archived = json.loads(archived_path.read_text(encoding="utf-8"))

    errors = validate_publication(current, health, archive_index, archived)
    if errors:
        detail = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"Weekly publication blocked:\n{detail}")


if __name__ == "__main__":
    validate_publication_files()
