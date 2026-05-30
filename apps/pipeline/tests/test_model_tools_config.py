"""Focused tests for centralized model/tools configuration behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news_pipeline.agents import model_tools_dynamic
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


if __name__ == "__main__":
    unittest.main()
