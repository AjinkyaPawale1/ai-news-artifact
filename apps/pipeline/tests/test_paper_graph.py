from __future__ import annotations

import unittest

from news_pipeline.agents.paper_graph import enrich_paper_item
from news_pipeline.push_to_artifact import build_dashboard_payload
from news_pipeline.schema import Item


class PaperGraphTests(unittest.TestCase):
    def test_enrich_paper_item_adds_deterministic_action_metadata(self) -> None:
        paper = Item(
            id="paper-1",
            source="arXiv",
            source_type="paper",
            title="Agentic RAG for Bank Compliance Audit Workflows",
            url="https://arxiv.org/pdf/2501.00001",
            raw_content=(
                "We present an open-source agent framework for retrieval "
                "augmented generation in banking compliance and audit reviews."
            ),
            tags=["cs.AI"],
        )

        enriched = enrich_paper_item(paper)
        metadata = enriched.metadata

        self.assertEqual(metadata["priority"], "SHARE")
        self.assertEqual(metadata["capability"], "Agentic AI")
        self.assertEqual(metadata["domain"], "Risk and Compliance")
        self.assertEqual(len(metadata["takeaways"]), 3)
        self.assertEqual(len(metadata["action_items"]), 3)
        self.assertTrue(metadata["has_code"])

    def test_dashboard_payload_uses_paper_action_metadata(self) -> None:
        paper = enrich_paper_item(
            Item(
                id="paper-2",
                source="arXiv",
                source_type="paper",
                title="Efficient RAG Evaluation for Portfolio Research",
                url="https://arxiv.org/pdf/2501.00002",
                raw_content=(
                    "A benchmark and implementation for retrieval evaluation "
                    "in portfolio research and investment workflows."
                ),
                tags=["cs.LG"],
            )
        ).to_dict()
        paper["score"] = 88
        paper["summary"] = "Fallback summary should not replace deterministic takeaways."

        payload = build_dashboard_payload([paper])
        dashboard_paper = payload["papers"][0]
        action_item = payload["actionItems"][0]

        self.assertEqual(dashboard_paper["takeaways"], paper["metadata"]["takeaways"])
        self.assertEqual(dashboard_paper["actionItems"], paper["metadata"]["action_items"])
        self.assertEqual(action_item["priority"], paper["metadata"]["priority"])
        self.assertEqual(action_item["title"], paper["metadata"]["action_items"][0])


if __name__ == "__main__":
    unittest.main()
