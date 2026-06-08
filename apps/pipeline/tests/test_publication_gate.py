from __future__ import annotations

import unittest

from news_pipeline.publication_gate import validate_publication


def _healthy_fixture() -> tuple[dict, list[dict], dict, dict]:
    current = {
        "generatedAt": "2026-06-08T14:00:00+00:00",
        "papers": [{"title": "Paper"}],
        "repos": [{"name": "org/repo"}],
        "blogs": [{"title": "Update"}],
        "models": [],
        "toolsServices": [{"name": "Tool"}],
    }
    health = [
        {
            "source": "papers",
            "status": "ok",
            "fetch_diagnostics": {
                "categories": [
                    {"category": "cs.AI", "status": "ok"},
                    {"category": "cs.CL", "status": "error"},
                ]
            },
        },
        {"source": "github", "status": "ok"},
        {"source": "rss", "status": "ok"},
        {"source": "model_tools", "status": "ok"},
    ]
    archive_index = {
        "editions": [
            {
                "date": "2026-06-08",
                "outputPath": "archive/2026-06-08/output.json",
            }
        ]
    }
    archived = dict(current)
    return current, health, archive_index, archived


class PublicationGateTests(unittest.TestCase):
    def test_accepts_complete_run_with_partial_internal_paper_category(self) -> None:
        self.assertEqual(validate_publication(*_healthy_fixture()), [])

    def test_rejects_missing_failed_and_duplicate_required_sources(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        health = [
            entry for entry in health if entry["source"] not in {"github", "rss", "model_tools"}
        ] + [
            {"source": "github", "status": "ok"},
            {"source": "github", "status": "ok"},
            {"source": "model_tools", "status": "error"},
        ]

        errors = validate_publication(current, health, archive_index, archived)

        self.assertIn("expected exactly one health entry for github, found 2", errors)
        self.assertIn("expected exactly one health entry for rss, found 0", errors)
        self.assertIn("required source model_tools is not healthy", errors)

    def test_rejects_empty_required_sections_and_releases(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        current.update({"papers": [], "repos": [], "blogs": [], "models": [], "toolsServices": []})
        archived = dict(current)

        errors = validate_publication(current, health, archive_index, archived)

        self.assertIn("current artifact has no papers", errors)
        self.assertIn("current artifact has no repos", errors)
        self.assertIn("current artifact has no blogs", errors)
        self.assertIn("current artifact has no model or tool/service releases", errors)

    def test_rejects_archive_mismatch(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        archived["generatedAt"] = "older"

        self.assertIn(
            "latest archive does not match current output",
            validate_publication(current, health, archive_index, archived),
        )


if __name__ == "__main__":
    unittest.main()
