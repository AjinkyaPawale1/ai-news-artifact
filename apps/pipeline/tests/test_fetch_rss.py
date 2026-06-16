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
        summary=f"Summary for {title}",
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
        ):
            items = fetch_rss.fetch_rss()
            diagnostics = fetch_rss.get_last_diagnostics()

        self.assertEqual([item.title for item in items], ["A0", "B0", "A1", "B1"])
        self.assertEqual(diagnostics["strategy"], "round_robin")
        self.assertEqual([entry["selected"] for entry in diagnostics["feeds"]], [2, 2])


if __name__ == "__main__":
    unittest.main()
