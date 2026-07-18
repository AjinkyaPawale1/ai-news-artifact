"""Focused tests for publication-safe fallback summaries."""

from __future__ import annotations

import unittest

from news_pipeline.summarize import MAX_SUMMARY_CHARS, summarize_items


class SummaryTests(unittest.TestCase):
    def test_fallback_summary_stops_at_last_complete_sentence(self) -> None:
        first = "A complete sentence with concrete AI deployment details."
        second = "Another complete sentence with evidence and implementation guidance."
        trailing = "An incomplete sentence that should not be displayed after the summary limit is reached " * 8

        summarized = summarize_items([{"raw_content": f"{first} {second} {trailing}"}])

        self.assertLessEqual(len(summarized[0]["summary"]), MAX_SUMMARY_CHARS)
        self.assertTrue(summarized[0]["summary"].endswith("."))
        self.assertNotIn("incomplete sentence", summarized[0]["summary"])


if __name__ == "__main__":
    unittest.main()
