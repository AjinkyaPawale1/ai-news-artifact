"""Tests for shared item normalization and validation."""

from __future__ import annotations

import unittest

from news_pipeline.normalize import normalize_items
from news_pipeline.schema import Item


class NormalizationTests(unittest.TestCase):
    def test_normalizes_shared_fields_and_dates(self) -> None:
        item = Item(
            id="  item-1  ",
            source="  Example   Feed ",
            source_type="rss",
            title="  Useful   AI update  ",
            url="http://www.example.com/update/?utm_medium=rss#details",
            authors=[" Ada  Lovelace ", "ada lovelace", ""],
            published_date="2026-07-20T10:00:00",
            fetched_date="2026-07-20T12:00:00Z",
            raw_content="  Detailed   content.  ",
            tags=[" Models ", "models", ""],
            related_links=[
                "https://example.com/update",
                "http://www.docs.example.com/update/?utm_source=rss#details",
                "https://docs.example.com/update",
                "not-a-url",
            ],
        )

        result = normalize_items([item])

        self.assertEqual(len(result), 1)
        normalized = result[0]
        self.assertEqual(normalized.id, "item-1")
        self.assertEqual(normalized.source, "Example Feed")
        self.assertEqual(normalized.title, "Useful AI update")
        self.assertEqual(normalized.url, "https://example.com/update")
        self.assertEqual(normalized.authors, ["Ada Lovelace"])
        self.assertEqual(normalized.tags, ["Models"])
        self.assertEqual(normalized.related_links, ["https://docs.example.com/update"])
        self.assertEqual(normalized.published_date, "2026-07-20T10:00:00+00:00")
        self.assertEqual(normalized.fetched_date, "2026-07-20T12:00:00+00:00")
        self.assertEqual(normalized.raw_content, "Detailed content.")

    def test_uses_fetched_date_and_unknown_author_fallbacks(self) -> None:
        item = Item(
            id="item-1",
            source="Example",
            source_type="paper",
            title="Paper",
            url="https://example.com/paper",
            published_date="not-a-date",
            fetched_date="2026-07-20T12:00:00+00:00",
        )

        normalized = normalize_items([item])[0]

        self.assertEqual(normalized.published_date, normalized.fetched_date)
        self.assertEqual(normalized.authors, ["Unknown"])

    def test_rejects_missing_required_fields_and_invalid_urls(self) -> None:
        valid = Item(id="ok", source="Example", source_type="github", title="Repo", url="https://github.com/a/b")
        invalid = [
            Item(id="", source="Example", source_type="rss", title="Title", url="https://example.com"),
            Item(id="bad", source="", source_type="rss", title="Title", url="https://example.com"),
            Item(id="bad", source="Example", source_type="rss", title="", url="https://example.com"),
            Item(id="bad", source="Example", source_type="rss", title="Title", url="not-a-url"),
            Item(id="bad", source="Example", source_type="unknown", title="Title", url="https://example.com"),
        ]

        self.assertEqual(normalize_items([*invalid, valid]), [valid])


if __name__ == "__main__":
    unittest.main()
