"""Tests for the source-suggestion approval script (scripts/apply_user_source.py)."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apply_user_source.py"
_spec = importlib.util.spec_from_file_location("apply_user_source", SCRIPT_PATH)
apply_user_source = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apply_user_source)

ISSUE_BODY_TEMPLATE = """### Source type

{source_type}

### URL or owner/repo

{value}

### Why is this relevant?

{reason}
"""


class ParseIssueBodyTests(unittest.TestCase):
    def test_parses_all_fields(self) -> None:
        body = ISSUE_BODY_TEMPLATE.format(
            source_type="RSS / blog feed", value="https://example.com/feed.xml", reason="Good coverage."
        )
        fields = apply_user_source.parse_issue_body(body)
        self.assertEqual(fields["Source type"], "RSS / blog feed")
        self.assertEqual(fields["URL or owner/repo"], "https://example.com/feed.xml")
        self.assertEqual(fields["Why is this relevant?"], "Good coverage.")


class ValidateTests(unittest.TestCase):
    def test_valid_github_repo(self) -> None:
        self.assertIsNone(apply_user_source.validate("github_repos", "owner/repo"))

    def test_invalid_github_repo(self) -> None:
        self.assertIsNotNone(apply_user_source.validate("github_repos", "not a repo"))

    def test_valid_url(self) -> None:
        self.assertIsNone(apply_user_source.validate("rss_feeds", "https://example.com/feed.xml"))

    def test_invalid_url_missing_scheme(self) -> None:
        self.assertIsNotNone(apply_user_source.validate("rss_feeds", "example.com/feed.xml"))


class MainFlowTests(unittest.TestCase):
    def _run(self, body: str, initial: dict | None = None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            body_path = Path(tmp) / "issue_body.txt"
            body_path.write_text(body, encoding="utf-8")
            sources_path = Path(tmp) / "user_sources.json"
            if initial is not None:
                sources_path.write_text(json.dumps(initial), encoding="utf-8")
            import sys

            old_argv = sys.argv
            sys.argv = ["apply_user_source.py", str(body_path), str(sources_path)]
            try:
                apply_user_source.main()
            finally:
                sys.argv = old_argv
            return json.loads(sources_path.read_text(encoding="utf-8")) if sources_path.exists() else {}

    def test_valid_suggestion_is_added(self) -> None:
        body = ISSUE_BODY_TEMPLATE.format(source_type="GitHub repository", value="owner/repo", reason="Active project.")
        result = self._run(body, initial={"rss_feeds": [], "github_repos": [], "model_tool_pages": []})
        self.assertIn("owner/repo", result["github_repos"])

    def test_invalid_suggestion_does_not_modify_file(self) -> None:
        body = ISSUE_BODY_TEMPLATE.format(source_type="GitHub repository", value="not a repo", reason="testing")
        result = self._run(body, initial={"rss_feeds": [], "github_repos": [], "model_tool_pages": []})
        self.assertEqual(result["github_repos"], [])

    def test_duplicate_suggestion_is_a_no_op(self) -> None:
        body = ISSUE_BODY_TEMPLATE.format(source_type="GitHub repository", value="owner/repo", reason="already tracked")
        result = self._run(body, initial={"rss_feeds": [], "github_repos": ["owner/repo"], "model_tool_pages": []})
        self.assertEqual(result["github_repos"], ["owner/repo"])


if __name__ == "__main__":
    unittest.main()
