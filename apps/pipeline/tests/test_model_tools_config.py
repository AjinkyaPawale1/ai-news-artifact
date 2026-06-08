"""Focused tests for centralized model/tools configuration behavior."""

from __future__ import annotations

from datetime import datetime, timezone
import json
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
    def test_weekly_archive_replaces_same_date_and_keeps_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "archive"
            index_path = archive_dir / "index.json"
            with (
                patch.object(push_to_artifact, "ARCHIVE_DIR", archive_dir),
                patch.object(push_to_artifact, "ARCHIVE_INDEX_PATH", index_path),
            ):
                first = {"generatedAt": "2026-06-01T14:00:00+00:00", "papers": [{"title": "First"}]}
                replacement = {"generatedAt": "2026-06-01T15:00:00+00:00", "papers": [{"title": "Replacement"}]}
                newer = {"generatedAt": "2026-06-08T14:00:00+00:00", "papers": [{"title": "Newer"}]}

                push_to_artifact.archive_dashboard_payload(first, [{"source": "papers"}])
                push_to_artifact.archive_dashboard_payload(replacement, [{"source": "papers"}])
                push_to_artifact.archive_dashboard_payload(newer, [{"source": "github"}])

            index = json.loads(index_path.read_text(encoding="utf-8"))
            archived = json.loads((archive_dir / "2026-06-01" / "output.json").read_text(encoding="utf-8"))

        self.assertEqual([entry["date"] for entry in index["editions"]], ["2026-06-08", "2026-06-01"])
        self.assertEqual(archived["papers"][0]["title"], "Replacement")
        self.assertEqual(len(index["editions"]), 2)

    def test_publication_monday_uses_new_york_date(self) -> None:
        generated_at = datetime(2026, 6, 8, 14, 0, tzinfo=timezone.utc).isoformat()

        self.assertEqual(push_to_artifact._publication_monday(generated_at), "2026-06-08")

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

    def test_repo_action_items_are_mapped_to_dashboard_payload(self) -> None:
        payload = push_to_artifact.build_dashboard_payload(
            [
                {
                    "source_type": "github",
                    "title": "org/repo",
                    "url": "https://github.com/org/repo",
                    "metadata": {
                        "item_kind": "repo",
                        "action_items": ["Run quickstart.", "Benchmark one task.", "Review issues."],
                    },
                }
            ]
        )

        self.assertEqual(payload["repos"][0]["actionItems"], ["Run quickstart.", "Benchmark one task.", "Review issues."])

    def test_model_release_links_hide_source_feed_and_add_benchmark(self) -> None:
        payload = push_to_artifact.build_dashboard_payload(
            [
                {
                    "source_type": "model",
                    "title": "Claude Opus 4.8",
                    "url": "https://example.com/release",
                    "metadata": {"source_url": "https://example.com/feed.xml", "source_label": "RSS feed"},
                }
            ]
        )

        expected_benchmark_url = "https://artificialanalysis.ai/models/claude-opus-4-8"
        self.assertEqual(
            payload["models"][0]["links"],
            [
                {"label": "Read release", "url": "https://example.com/release"},
                {"label": "Benchmark", "url": expected_benchmark_url},
            ],
        )
        self.assertEqual(payload["models"][0]["benchmarkUrl"], expected_benchmark_url)

    def test_unknown_model_release_falls_back_to_benchmark_directory(self) -> None:
        payload = push_to_artifact.build_dashboard_payload(
            [
                {
                    "source_type": "model",
                    "title": "Mellum2",
                    "url": "https://example.com/mellum2",
                }
            ]
        )

        self.assertEqual(
            payload["models"][0]["links"],
            [
                {"label": "Read release", "url": "https://example.com/mellum2"},
                {"label": "Benchmarks", "url": "https://artificialanalysis.ai/models"},
            ],
        )

    def test_tool_release_links_keep_only_read_release(self) -> None:
        payload = push_to_artifact.build_dashboard_payload(
            [
                {
                    "source_type": "tool_service",
                    "title": "Tool",
                    "url": "https://example.com/tool",
                    "metadata": {"source_url": "https://example.com/feed.xml", "source_label": "RSS feed"},
                }
            ]
        )

        self.assertEqual(payload["toolsServices"][0]["links"], [{"label": "Read release", "url": "https://example.com/tool"}])


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

    def test_classifier_moves_hosted_model_availability_to_tools(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "AWS",
                "title": "Fundamental's large tabular model NEXUS is now available on Amazon SageMaker JumpStart",
                "content": "Fundamental's NEXUS foundation model is now available on Amazon SageMaker JumpStart.",
                "url": "https://example.com/nexus",
            },
            model_terms=["model", "foundation model", "nexus"],
            tool_terms=["deployment", "sagemaker", "jumpstart"],
        )

        self.assertEqual(release["kind"], "tool_service")

    def test_classifier_rejects_model_capability_update_without_new_model(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "OpenAI",
                "title": "Introducing new capabilities to GPT-Rosalind",
                "content": "OpenAI shipped new capabilities for biology workflows.",
                "url": "https://example.com/gpt-rosalind",
            },
            model_terms=["model", "gpt"],
            tool_terms=["workflow"],
        )

        self.assertIsNone(release)

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
