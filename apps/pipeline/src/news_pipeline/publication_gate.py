"""Validate that a generated weekly artifact is safe to publish."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .push_to_artifact import (
    ARCHIVE_INDEX_PATH,
    DATA_DIR,
    FALLBACK_MAX_AGE_DAYS,
    FALLBACK_SECTIONS,
    OUTPUT_PATH,
    _publication_monday,
)

HEALTH_PATH = DATA_DIR / "health.json"
REQUIRED_SOURCES = {"papers", "github", "rss", "model_tools"}
MIN_BLOG_SUMMARY_CHARS = 120


def _validate_fallback_sections(current: dict[str, Any], errors: list[str]) -> None:
    fallback_sections = current.get("fallbackSections", {})
    if not isinstance(fallback_sections, dict):
        errors.append("fallbackSections must be an object")
        return
    try:
        current_edition_date = date.fromisoformat(_publication_monday(current["generatedAt"]))
    except (KeyError, TypeError, ValueError):
        errors.append("current artifact has an invalid generatedAt timestamp")
        return

    for section, provenance in fallback_sections.items():
        if section not in FALLBACK_SECTIONS:
            errors.append(f"fallback section {section} is not supported")
            continue
        if not isinstance(provenance, dict):
            errors.append(f"fallback section {section} has invalid provenance")
            continue
        try:
            source_date = date.fromisoformat(provenance["editionDate"])
            source_generated_at = provenance["generatedAt"]
        except (KeyError, TypeError, ValueError):
            errors.append(f"fallback section {section} has invalid provenance")
            continue
        if not isinstance(source_generated_at, str) or not source_generated_at:
            errors.append(f"fallback section {section} has invalid provenance")
            continue
        age = (current_edition_date - source_date).days
        if age < 0 or age > FALLBACK_MAX_AGE_DAYS:
            errors.append(f"fallback section {section} is outside the allowed age window")


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
        "models": current.get("models"),
        "toolsServices": current.get("toolsServices"),
        "blogs": current.get("blogs"),
    }
    for section, items in required_sections.items():
        if not isinstance(items, list) or not items:
            errors.append(f"current artifact has no {section}")

    for index, blog in enumerate(current.get("blogs") or []):
        summary = " ".join(blog.get("takeaways") or [])
        if not blog.get("url") or not blog.get("linkVerified"):
            errors.append(f"blog {index + 1} has an unverified link")
        normalized_summary = " ".join(summary.split())
        if len(normalized_summary) < MIN_BLOG_SUMMARY_CHARS or not normalized_summary.endswith((".", "!", "?")):
            errors.append(f"blog {index + 1} has an insufficient summary")

    _validate_fallback_sections(current, errors)

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
