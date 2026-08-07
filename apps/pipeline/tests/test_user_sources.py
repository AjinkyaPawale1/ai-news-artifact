"""Tests for the maintainer-approved user-sources loader."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news_pipeline import user_sources


class UserSourcesTests(unittest.TestCase):
    def test_load_user_sources_missing_file_returns_empty(self) -> None:
        with patch.object(user_sources, "USER_SOURCES_PATH", Path("/nonexistent/user_sources.json")):
            self.assertEqual(user_sources.load_user_sources(), {})

    def test_load_user_sources_malformed_json_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "user_sources.json"
            path.write_text("not json")
            with patch.object(user_sources, "USER_SOURCES_PATH", path):
                self.assertEqual(user_sources.load_user_sources(), {})

    def test_merged_appends_deduped_entries_preserving_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "user_sources.json"
            path.write_text(json.dumps({"rss_feeds": ["https://existing.example/feed.xml", "https://new.example/feed.xml"]}))
            with patch.object(user_sources, "USER_SOURCES_PATH", path):
                result = user_sources.merged(["https://existing.example/feed.xml"], "rss_feeds")
        self.assertEqual(result, ["https://existing.example/feed.xml", "https://new.example/feed.xml"])

    def test_merged_ignores_non_string_and_blank_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "user_sources.json"
            path.write_text(json.dumps({"github_repos": ["owner/repo", "  ", 123, None]}))
            with patch.object(user_sources, "USER_SOURCES_PATH", path):
                result = user_sources.merged([], "github_repos")
        self.assertEqual(result, ["owner/repo"])

    def test_merged_missing_key_returns_base_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "user_sources.json"
            path.write_text(json.dumps({"rss_feeds": ["https://a.example/feed.xml"]}))
            with patch.object(user_sources, "USER_SOURCES_PATH", path):
                result = user_sources.merged(["seed"], "model_tool_pages")
        self.assertEqual(result, ["seed"])


if __name__ == "__main__":
    unittest.main()
