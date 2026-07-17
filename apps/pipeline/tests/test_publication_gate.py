from __future__ import annotations

import unittest

from news_pipeline.publication_gate import validate_publication


def _healthy_fixture() -> tuple[dict, list[dict], dict, dict]:
    current = {
        "generatedAt": "2026-06-08T14:00:00+00:00",
        "papers": [{"title": "Paper"}],
        "repos": [{"name": "org/repo"}],
        "blogs": [
            {
                "title": "Update",
                "url": "https://example.com/update",
                "linkVerified": True,
                "takeaways": ["A sufficiently detailed AI release update with production, deployment, and evaluation implications for enterprise teams."],
            }
        ],
        "models": [{"name": "Model"}],
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

    def test_rejects_empty_required_sections_and_each_release_category(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        current.update({"papers": [], "repos": [], "blogs": [], "models": [], "toolsServices": []})
        archived = dict(current)

        errors = validate_publication(current, health, archive_index, archived)

        self.assertIn("current artifact has no papers", errors)
        self.assertIn("current artifact has no repos", errors)
        self.assertIn("current artifact has no blogs", errors)
        self.assertIn("current artifact has no models", errors)
        self.assertIn("current artifact has no toolsServices", errors)

    def test_rejects_stale_fallback_provenance(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        current["fallbackSections"] = {
            "models": {
                "editionDate": "2026-05-04",
                "generatedAt": "2026-05-04T14:00:00+00:00",
                "reason": "no_current_valid_items",
            }
        }
        archived = dict(current)

        self.assertIn(
            "fallback section models is outside the allowed age window",
            validate_publication(current, health, archive_index, archived),
        )

    def test_rejects_archive_mismatch(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        archived["generatedAt"] = "older"

        self.assertIn(
            "latest archive does not match current output",
            validate_publication(current, health, archive_index, archived),
        )

    def test_rejects_unverified_or_sparse_blog_content(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        current["blogs"] = [{"title": "Weak", "url": "https://example.com/weak", "linkVerified": False, "takeaways": ["Too short."]}]
        archived = dict(current)

        errors = validate_publication(current, health, archive_index, archived)

        self.assertIn("blog 1 has an unverified link", errors)
        self.assertIn("blog 1 has an insufficient summary", errors)

    def test_rejects_blog_copy_cut_mid_sentence(self) -> None:
        current, health, archive_index, archived = _healthy_fixture()
        current["blogs"][0]["takeaways"] = [
            "A detailed AI release update with production deployment and evaluation information that ends without a completed sentence"
        ]
        archived = dict(current)

        self.assertIn(
            "blog 1 has an insufficient summary",
            validate_publication(current, health, archive_index, archived),
        )


if __name__ == "__main__":
    unittest.main()
