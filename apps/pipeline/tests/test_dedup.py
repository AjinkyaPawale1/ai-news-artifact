"""Tests for shared cross-source deduplication."""

from __future__ import annotations

import unittest

from news_pipeline.dedup import canonicalize_url, deduplicate_items
from news_pipeline.schema import Item


def _item(source_type: str, title: str, url: str, **kwargs) -> Item:
    return Item(
        id=kwargs.pop("id", url),
        source=kwargs.pop("source", source_type),
        source_type=source_type,
        title=title,
        url=url,
        **kwargs,
    )


class DeduplicationTests(unittest.TestCase):
    def test_canonicalizes_tracking_fragments_and_arxiv_variants(self) -> None:
        self.assertEqual(
            canonicalize_url("http://www.example.com/post/?utm_source=email&b=2&a=1#top"),
            "https://example.com/post?a=1&b=2",
        )
        self.assertEqual(
            canonicalize_url("https://export.arxiv.org/pdf/2607.12345v2.pdf"),
            "https://arxiv.org/abs/2607.12345",
        )

    def test_merges_canonical_url_duplicates_and_preserves_related_links(self) -> None:
        rss = _item(
            "rss",
            "Acme launches Model X",
            "https://example.com/model-x?utm_source=rss",
            related_links=["https://example.com/context"],
        )
        model = _item(
            "model",
            "Model X is now available",
            "https://example.com/model-x#release",
            raw_content="A detailed release description.",
            related_links=["https://example.com/changelog"],
        )

        result = deduplicate_items([rss, model])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].source_type, "model")
        self.assertEqual(
            result[0].related_links,
            ["https://example.com/changelog", "https://example.com/context"],
        )

    def test_merges_only_high_confidence_titles_in_compatible_families(self) -> None:
        first = _item(
            "rss",
            "Acme introduces Model X for secure enterprise deployment",
            "https://news.example.com/acme-model-x",
        )
        second = _item(
            "model",
            "Acme introduces the Model X for secure enterprise deployments",
            "https://acme.example.com/model-x",
        )
        unrelated = _item(
            "paper",
            "Acme introduces Model X for secure enterprise deployment",
            "https://arxiv.org/abs/2607.99999",
        )

        result = deduplicate_items([first, second, unrelated])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].source_type, "model")
        self.assertEqual(result[0].related_links, [first.url])
        self.assertEqual(result[1].source_type, "paper")

    def test_short_generic_titles_do_not_fuzzy_match(self) -> None:
        items = [
            _item("rss", "New AI model release", "https://a.example.com/release"),
            _item("model", "New AI model released", "https://b.example.com/release"),
        ]

        self.assertEqual(len(deduplicate_items(items)), 2)


if __name__ == "__main__":
    unittest.main()
