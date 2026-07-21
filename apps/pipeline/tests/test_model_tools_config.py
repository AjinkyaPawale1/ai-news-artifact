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
from news_pipeline.model_tools_config import MODEL_TOOL_SOURCE_PAGES


class ModelToolsDynamicTests(unittest.TestCase):
    def test_permanent_source_pages_include_perplexity_and_elevenlabs(self) -> None:
        self.assertIn("https://docs.perplexity.ai/docs/resources/changelog.md", MODEL_TOOL_SOURCE_PAGES)
        self.assertIn("https://elevenlabs.io/blog/", MODEL_TOOL_SOURCE_PAGES)

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
    @staticmethod
    def _fallback_payload(generated_at: str, **sections: object) -> dict:
        return {
            "generatedAt": generated_at,
            "health": [
                {"source": "papers", "status": "ok"},
                {"source": "github", "status": "ok"},
                {"source": "rss", "status": "ok"},
                {"source": "model_tools", "status": "ok"},
            ],
            "papers": [],
            "repos": [],
            "models": [],
            "toolsServices": [],
            "blogs": [],
            **sections,
        }

    def _apply_fallback(self, current: dict, archived: dict, archive_date: str) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            archive_dir = data_dir / "archive"
            archive_path = archive_dir / archive_date / "output.json"
            archive_path.parent.mkdir(parents=True)
            archive_path.write_text(json.dumps(archived), encoding="utf-8")
            index_path = archive_dir / "index.json"
            index_path.write_text(
                json.dumps({"editions": [{"date": archive_date, "outputPath": f"archive/{archive_date}/output.json"}]}),
                encoding="utf-8",
            )
            with (
                patch.object(push_to_artifact, "DATA_DIR", data_dir),
                patch.object(push_to_artifact, "OUTPUT_PATH", data_dir / "output.json"),
                patch.object(push_to_artifact, "ARCHIVE_DIR", archive_dir),
                patch.object(push_to_artifact, "ARCHIVE_INDEX_PATH", index_path),
            ):
                return push_to_artifact.apply_section_fallbacks(current)

    def test_empty_model_section_uses_latest_valid_prior_models_only(self) -> None:
        current = self._fallback_payload(
            "2026-07-13T14:00:00+00:00",
            toolsServices=[{"name": "Current Tool", "url": "https://example.com/tool", "note": "Current release."}],
        )
        archived = self._fallback_payload(
            "2026-07-06T14:00:00+00:00",
            models=[{"name": "Prior Model", "url": "https://example.com/model", "note": "Prior release."}],
        )

        updated = self._apply_fallback(current, archived, "2026-07-06")

        self.assertEqual([item["name"] for item in updated["models"]], ["Prior Model"])
        self.assertEqual([item["name"] for item in updated["toolsServices"]], ["Current Tool"])
        self.assertEqual(
            updated["fallbackSections"]["models"],
            {
                "editionDate": "2026-07-06",
                "generatedAt": "2026-07-06T14:00:00+00:00",
                "reason": "no_current_valid_items",
            },
        )

    def test_fallback_rejects_stale_historical_sections(self) -> None:
        current = self._fallback_payload("2026-07-13T14:00:00+00:00")
        stale = self._fallback_payload(
            "2026-06-01T14:00:00+00:00",
            models=[{"name": "Old Model", "url": "https://example.com/model", "note": "Old release."}],
        )

        updated = self._apply_fallback(current, stale, "2026-06-01")

        self.assertEqual(updated["models"], [])
        self.assertEqual(updated["fallbackSections"], {})

    def test_fallback_rejects_invalid_historical_blog(self) -> None:
        current = self._fallback_payload("2026-07-13T14:00:00+00:00")
        archived = self._fallback_payload(
            "2026-07-06T14:00:00+00:00",
            blogs=[
                {
                    "title": "Unverified",
                    "url": "https://example.com/blog",
                    "linkVerified": False,
                    "takeaways": ["A sufficiently detailed but unverified AI update that should not enter a public brief."],
                }
            ],
        )

        updated = self._apply_fallback(current, archived, "2026-07-06")

        self.assertEqual(updated["blogs"], [])
        self.assertNotIn("blogs", updated["fallbackSections"])

    def test_fallback_preserves_original_provenance_across_same_week_reruns(self) -> None:
        current = self._fallback_payload("2026-07-13T17:00:00+00:00")
        previous_run = self._fallback_payload(
            "2026-07-13T14:00:00+00:00",
            models=[{"name": "Prior Model", "url": "https://example.com/model", "note": "Prior release."}],
            fallbackSections={
                "models": {
                    "editionDate": "2026-07-06",
                    "generatedAt": "2026-07-06T14:00:00+00:00",
                    "reason": "no_current_valid_items",
                }
            },
        )

        updated = self._apply_fallback(current, previous_run, "2026-07-13")

        self.assertEqual(updated["fallbackSections"]["models"]["editionDate"], "2026-07-06")
        self.assertEqual(updated["fallbackSections"]["models"]["generatedAt"], "2026-07-06T14:00:00+00:00")

    def test_fallback_ignores_malformed_archive_index_entries(self) -> None:
        current = self._fallback_payload("2026-07-13T14:00:00+00:00")
        archived = self._fallback_payload(
            "2026-07-06T14:00:00+00:00",
            models=[{"name": "Prior Model", "url": "https://example.com/model", "note": "Prior release."}],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            archive_dir = data_dir / "archive"
            archive_path = archive_dir / "2026-07-06" / "output.json"
            archive_path.parent.mkdir(parents=True)
            archive_path.write_text(json.dumps(archived), encoding="utf-8")
            index_path = archive_dir / "index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "editions": [
                            None,
                            "invalid",
                            {"date": "2026-07-06", "outputPath": "archive/2026-07-06/output.json"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(push_to_artifact, "DATA_DIR", data_dir),
                patch.object(push_to_artifact, "OUTPUT_PATH", data_dir / "output.json"),
                patch.object(push_to_artifact, "ARCHIVE_DIR", archive_dir),
                patch.object(push_to_artifact, "ARCHIVE_INDEX_PATH", index_path),
            ):
                updated = push_to_artifact.apply_section_fallbacks(current)

        self.assertEqual([item["name"] for item in updated["models"]], ["Prior Model"])

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

    def test_repo_selection_limits_agent_memory_cluster(self) -> None:
        items = [
            {
                "source_type": "github",
                "title": f"org/memory-{index}",
                "raw_content": "A long-term memory and knowledge graph system for AI agents.",
                "metadata": {"item_kind": "repo", "traction_score": 100 - index},
            }
            for index in range(3)
        ]
        items += [
            {
                "source_type": "github",
                "title": f"org/tool-{index}",
                "raw_content": "An AI evaluation and deployment tool.",
                "metadata": {"item_kind": "repo", "traction_score": 90 - index},
            }
            for index in range(2)
        ]

        payload = push_to_artifact.build_dashboard_payload(items)

        self.assertEqual([repo["name"] for repo in payload["repos"]], ["org/memory-0", "org/memory-1", "org/tool-0", "org/tool-1"])

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
                {"label": "Model directory", "url": "https://artificialanalysis.ai/models"},
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
    def test_markdown_changelog_emits_dated_release_candidates(self) -> None:
        markdown = """
<Update label="May 2026" tags={["Agent API", "Tools"]}>
  **Finance Search: Now Available**

  The `finance_search` tool is now available in the Agent API.

  **Highlights:**

  * Structured market data
</Update>
"""
        with patch.object(model_tools_graph, "datetime") as mocked_datetime:
            mocked_datetime.strptime.side_effect = datetime.strptime
            mocked_datetime.now.return_value = datetime(2026, 6, 8, tzinfo=timezone.utc)
            entries = model_tools_graph._fetch_markdown_changelog_entries(
                "https://docs.perplexity.ai/docs/resources/changelog.md",
                markdown,
            )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"], "Perplexity")
        self.assertEqual(entries[0]["title"], "Finance Search: Now Available")
        self.assertEqual(entries[0]["published_date"], "2026-05-31T00:00:00+00:00")

    def test_markdown_changelog_waits_until_month_has_completed(self) -> None:
        with patch.object(model_tools_graph, "datetime") as mocked_datetime:
            mocked_datetime.strptime.side_effect = datetime.strptime
            mocked_datetime.now.return_value = datetime(2026, 5, 31, 18, 0, tzinfo=timezone.utc)
            published_date = model_tools_graph._month_end_date("May 2026")

        self.assertEqual(published_date, "")

    def test_source_page_release_uses_article_body_for_focus_signal(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "ElevenLabs",
                "title": "Introducing Dubbing v2",
                "content": "Today we are launching Dubbing v2, a new AI dubbing model.",
                "url": "https://elevenlabs.io/blog/introducing-dubbing-v2",
                "source_page": True,
            },
            model_terms=["model"],
            tool_terms=["platform"],
        )

        self.assertEqual(release["kind"], "model")
        self.assertEqual(release["org"], "ElevenLabs")

    def test_source_page_rejects_corporate_expansion_announcement(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "ElevenLabs",
                "title": "ElevenLabs announces new expansion in Australia and New Zealand",
                "content": "The company provides speech models and an AI voice platform.",
                "url": "https://elevenlabs.io/blog/australia-new-zealand-expansion",
                "source_page": True,
            },
            model_terms=["model"],
            tool_terms=["platform"],
        )

        self.assertIsNone(release)

    def test_source_page_rejects_partnership_announcement(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "ElevenLabs",
                "title": "Announcing a new partnership with Example Corp",
                "content": "The partnership will use ElevenLabs speech models and platform.",
                "url": "https://elevenlabs.io/blog/example-partnership",
                "source_page": True,
            },
            model_terms=["model"],
            tool_terms=["platform"],
        )

        self.assertIsNone(release)

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

    def test_classifier_accepts_versioned_frontier_model_without_release_verb(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "OpenAI",
                "title": "GPT-5.6: Frontier intelligence that scales with your ambition",
                "content": "More intelligence from every token and stronger performance per dollar.",
                "url": "https://openai.com/index/gpt-5-6",
            },
            model_terms=["model", "gpt"],
            tool_terms=["api", "platform"],
        )

        self.assertEqual(release["kind"], "model")
        self.assertTrue(release["major_release"])
        self.assertEqual(release["major_model_family"], "gpt56")
        self.assertGreaterEqual(release["impact_score"], 80)

    def test_major_model_name_ignores_surrounding_source_page_copy(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "Anthropic",
                "title": (
                    "Product Jun 30, 2026 Introducing Claude Sonnet 5 "
                    "Sonnet 5 delivers frontier performance across coding and agents."
                ),
                "content": "Claude Sonnet 5 is a frontier model for professional and enterprise users.",
                "url": "https://www.anthropic.com/news/claude-sonnet-5",
                "source_page": True,
            },
            model_terms=["model", "claude", "sonnet"],
            tool_terms=["agent"],
        )

        self.assertEqual(release["name"], "Claude Sonnet 5")
        self.assertTrue(release["major_release"])

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_classifier_carries_major_models_but_not_ordinary_tools_for_28_days(self) -> None:
        state = {
            "entries": [
                {
                    "source": "OpenAI",
                    "title": "GPT-5.6: Frontier intelligence that scales with your ambition",
                    "content": "More intelligence from every token and stronger performance per dollar.",
                    "url": "https://openai.com/index/gpt-5-6",
                    "published_date": "2026-07-09T10:00:00+00:00",
                },
                {
                    "source": "Google",
                    "title": "Introducing Example Agent Platform 2",
                    "content": "A new developer API and agent platform is available.",
                    "url": "https://example.com/agent-platform-2",
                    "published_date": "2026-07-09T10:00:00+00:00",
                },
            ],
            "model_terms": [],
            "tool_terms": [],
        }

        with patch.object(
            model_tools_graph,
            "window_start",
            return_value=datetime(2026, 7, 13, tzinfo=timezone.utc),
        ):
            classified = model_tools_graph._classify_entries(state)

        self.assertEqual([entry["name"] for entry in classified["classified"]], ["GPT-5.6"])
        self.assertEqual(classified["classification_diagnostics"]["major_model_carried_forward"], 1)
        self.assertEqual(classified["classification_diagnostics"]["rejected_missing_or_stale_date"], 1)

    def test_classifier_rejects_consumer_or_education_announcements(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "Google",
                "title": "We’re expanding Gemini in Chrome to users in the U.K.",
                "content": "Google is rolling out AI features to more consumer Chrome users.",
                "url": "https://example.com/gemini-chrome",
            },
            model_terms=["gemini", "model"],
            tool_terms=["platform"],
        )

        self.assertIsNone(release)

    def test_classifier_requires_a_release_signal_in_the_headline(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "Google",
                "title": "Systems Engineering Playbook: Optimizing Qwen 3.5 on TPUs",
                "content": "The Qwen model release explains deployment and inference optimization.",
                "url": "https://example.com/qwen-playbook",
            },
            model_terms=["qwen", "model"],
            tool_terms=["deployment", "inference"],
        )

        self.assertIsNone(release)

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

    def test_classifier_keeps_model_catalog_integration_as_tool_service(self) -> None:
        release = model_tools_graph._classify_entry(
            {
                "source": "Perplexity",
                "title": "New Integration: n8n",
                "content": "The integration adds Agent API and model catalog support.",
                "url": "https://example.com/n8n",
                "source_page": True,
            },
            model_terms=["model"],
            tool_terms=["integration", "api"],
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

    def test_selection_prioritizes_major_model_and_supersedes_its_preview(self) -> None:
        state = {
            "classified": [
                {
                    "kind": "model",
                    "name": "Previewing GPT-5.6 Sol",
                    "org": "OpenAI",
                    "published_date": "2026-06-26T10:00:00+00:00",
                    "release_score": 20,
                    "major_release": True,
                    "major_model_family": "gpt56",
                    "impact_score": 55,
                },
                {
                    "kind": "model",
                    "name": "GPT-5.6",
                    "org": "OpenAI",
                    "published_date": "2026-07-09T10:00:00+00:00",
                    "release_score": 12,
                    "major_release": True,
                    "major_model_family": "gpt56",
                    "impact_score": 80,
                },
                {
                    "kind": "model",
                    "name": "Current specialist model",
                    "org": "Example",
                    "published_date": "2026-07-16T10:00:00+00:00",
                    "release_score": 30,
                    "major_release": False,
                    "major_model_family": "",
                    "impact_score": 0,
                },
            ]
        }

        selected = model_tools_graph._select_entries(state)

        self.assertEqual(
            [entry["name"] for entry in selected["selected"]],
            ["GPT-5.6", "Current specialist model"],
        )
        self.assertEqual(selected["selection_diagnostics"]["major_models_selected"], 1)
        self.assertEqual(selected["selection_diagnostics"]["rejected_superseded_major_model"], 1)


if __name__ == "__main__":
    unittest.main()
