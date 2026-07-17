"""Focused tests for fair RSS collection."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from news_pipeline.agents import fetch_rss

_NOW = datetime.now(timezone.utc)
_PUBLISHED = (_NOW.year, _NOW.month, _NOW.day, _NOW.hour, _NOW.minute, _NOW.second)


def _entry(title: str, url: str) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        link=url,
        published_parsed=_PUBLISHED,
        tags=[],
        summary=(
            f"{title} describes a new AI research or developer update with concrete deployment, "
            "evaluation, and production implications for technical teams."
        ),
        author="Author",
    )


class RssCollectionTests(unittest.TestCase):
    def test_round_robin_selection_keeps_multiple_feeds_visible(self) -> None:
        feeds = ["https://example.com/a.xml", "https://example.com/b.xml"]

        def parse(url: str) -> SimpleNamespace:
            label = "A" if url.endswith("a.xml") else "B"
            return SimpleNamespace(
                feed={"title": f"Feed {label}"},
                entries=[_entry(f"{label}{index}", f"https://example.com/{label.lower()}/{index}") for index in range(4)],
            )

        with (
            patch.object(fetch_rss, "RSS_FEEDS", feeds),
            patch.object(fetch_rss, "MAX_ITEMS_PER_SOURCE", 4),
            patch.object(fetch_rss.feedparser, "parse", side_effect=parse),
            patch.object(fetch_rss, "_verify_link", return_value=(True, 200)),
        ):
            items = fetch_rss.fetch_rss()
            diagnostics = fetch_rss.get_last_diagnostics()

        self.assertEqual([item.title for item in items], ["A0", "B0", "A1", "B1"])
        self.assertEqual(diagnostics["strategy"], "round_robin")
        self.assertEqual([entry["selected"] for entry in diagnostics["feeds"]], [2, 2])

    def test_rejects_tutorials_and_unverified_links(self) -> None:
        feed = "https://example.com/a.xml"
        entries = [
            _entry("Getting started with ChatGPT", "https://example.com/tutorial"),
            _entry("AI model deployment update", "https://example.com/failed-link"),
            _entry("AI model deployment update", "https://example.com/eligible"),
        ]

        def parse(_: str) -> SimpleNamespace:
            return SimpleNamespace(feed={"title": "Feed A"}, entries=entries)

        with (
            patch.object(fetch_rss, "RSS_FEEDS", [feed]),
            patch.object(fetch_rss.feedparser, "parse", side_effect=parse),
            patch.object(fetch_rss, "_verify_link", side_effect=[(False, 404), (True, 200)]),
        ):
            items = fetch_rss.fetch_rss()
            diagnostics = fetch_rss.get_last_diagnostics()

        self.assertEqual([item.url for item in items], ["https://example.com/eligible"])
        self.assertEqual(diagnostics["feeds"][0]["rejected"], {"link_verification_failed": 1, "tutorial_or_onboarding": 1})
        self.assertTrue(items[0].metadata["link_verified"])

    def test_replaces_sparse_feed_copy_with_canonical_metadata(self) -> None:
        sparse = SimpleNamespace(
            title="AI model release",
            link="https://example.com/release",
            published_parsed=_PUBLISHED,
            tags=[],
            summary="AI model release",
            author="Author",
        )
        response = SimpleNamespace(
            status_code=200,
            text='<html><meta property="og:description" content="A new AI model release adds production deployment controls, developer tooling, and evaluation guidance for enterprise teams."></html>',
        )

        with (
            patch.object(fetch_rss, "RSS_FEEDS", ["https://example.com/a.xml"]),
            patch.object(fetch_rss.feedparser, "parse", return_value=SimpleNamespace(feed={"title": "Feed A"}, entries=[sparse])),
            patch.object(fetch_rss.requests, "get", return_value=response),
            patch.object(fetch_rss, "_verify_link", return_value=(True, 200)),
        ):
            items = fetch_rss.fetch_rss()

        self.assertEqual(len(items), 1)
        self.assertIn("production deployment controls", items[0].raw_content)


if __name__ == "__main__":
    unittest.main()
