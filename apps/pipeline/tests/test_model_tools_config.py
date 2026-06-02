"""Focused tests for centralized model/tools configuration behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news_pipeline.agents import model_tools_dynamic, model_tools_graph
from news_pipeline import push_to_artifact


class ModelToolsDynamicTests(unittest.TestCase):
    def test_bounded_rotation_replaces_only_the_allowed_number(self) -> None:
        rotated, metadata = model_tools_dynamic._bounded_rotation(
            ["feed-a", "feed-b", "feed-c"],
            ["feed-d", "feed-e"],
            max_items=3,
            max_replacements=1,
        )

        self.assertEqual(rotated, ["feed-d", "feed-a", "feed-b"])
        self.assertEqual(metadata["replacements"], 1)
        self.assertEqual(metadata["added"], ["feed-d"])
        self.assertEqual(metadata["removed"], ["feed-c"])

    def test_resolver_deduplicates_core_and_emerging_feeds(self) -> None:
        core = "https://example.com/core.xml"
        emerging = "https://example.com/emerging.xml"
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "model_tools_dynamic_config.json"
            with (
                patch.object(model_tools_dynamic, "_DYNAMIC_CONFIG_PATH", state_path),
                patch.object(model_tools_dynamic, "MODEL_TOOL_CORE_FEEDS", [core]),
                patch.object(model_tools_dynamic, "MODEL_TOOL_EMERGING_FEEDS", [core, emerging]),
                patch.object(model_tools_dynamic, "MODEL_TOOL_FEED_CANDIDATES", [core, emerging]),
                patch.object(model_tools_dynamic, "MODEL_TOOL_SOURCE_PAGES", []),
                patch.object(model_tools_dynamic, "MODEL_TOOL_DYNAMIC_AUTO_UPDATE", False),
            ):
                resolved = model_tools_dynamic.resolve_dynamic_model_tool_inputs()

        self.assertEqual(resolved["feeds"], [core, emerging])


class DashboardArtifactTests(unittest.TestCase):
    def test_shared_model_tool_limit_controls_each_release_category(self) -> None:
        items = [
            {"source_type": "model", "title": f"Model {index}", "url": f"https://example.com/model-{index}"}
            for index in range(3)
        ]
        items += [
            {
                "source_type": "tool_service",
                "title": f"Tool {index}",
                "url": f"https://example.com/tool-{index}",
            }
            for index in range(3)
        ]

        with patch.object(push_to_artifact, "MODEL_TOOL_MAX_ITEMS", 2):
            payload = push_to_artifact.build_dashboard_payload(items)

        self.assertEqual(len(payload["models"]), 2)
        self.assertEqual(len(payload["toolsServices"]), 2)

    def test_dashboard_stats_describe_selected_content_and_health(self) -> None:
        items = [
            {"source_type": "paper", "title": "Paper", "metadata": {"research_score": 1}},
            {"source_type": "github", "title": "org/repo", "metadata": {"item_kind": "repo"}},
            {"source_type": "model", "title": "Model"},
            {"source_type": "tool_service", "title": "Tool"},
        ]
        health = [{"source": "papers", "status": "ok"}, {"source": "rss", "status": "error"}]

        payload = push_to_artifact.build_dashboard_payload(items, health)

        self.assertEqual(
            payload["stats"],
            [
                {"label": "PAPERS REVIEWED", "value": "1", "sub": "1 selected"},
                {"label": "REPOS INDEXED", "value": "1", "sub": "1 shown"},
                {"label": "RELEASES TRACKED", "value": "2", "sub": "1 models · 1 tools"},
                {"label": "HEALTHY SOURCES", "value": "1/2", "sub": "latest pipeline run", "accent": True},
            ],
        )


class ModelToolsClassificationTests(unittest.TestCase):
    def test_classifier_rejects_guide_without_release_headline(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "AWS",
                "title": "Accelerate LLM model loading with GPUDirect",
                "content": "A guide for deploying models that includes updated examples.",
                "url": "https://example.com/guide",
            },
            model_terms=["model", "llm"],
            tool_terms=["deployment"],
        )

        self.assertIsNone(release)

    def test_classifier_accepts_concrete_release_headline(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "NVIDIA",
                "title": "Introducing NVIDIA Cosmos 3",
                "content": "NVIDIA released a new foundation model for physical AI.",
                "url": "https://example.com/cosmos",
            },
            model_terms=["model", "cosmos"],
            tool_terms=["platform"],
        )

        self.assertEqual(release["kind"], "model")

    def test_selection_collapses_same_day_near_duplicate_but_preserves_versions(self) -> None:
        base = {
            "kind": "tool_service",
            "org": "OpenAI",
            "published_date": "2026-06-02T00:00:00+00:00",
            "release_score": 10,
        }
        state = {
            "classified": [
                {**base, "name": "Codex for every role, tool, and workflow"},
                {**base, "name": "Codex", "release_score": 9},
                {**base, "name": "Codex 2.0", "release_score": 8},
            ]
        }

        selected = model_tools_graph._select_entries(state)

        self.assertEqual([entry["name"] for entry in selected["selected"]], [
            "Codex for every role, tool, and workflow",
            "Codex 2.0",
        ])
        self.assertEqual(selected["selection_diagnostics"]["rejected_near_duplicate"], 1)


if __name__ == "__main__":
    unittest.main()
