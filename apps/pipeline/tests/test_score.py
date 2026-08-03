"""Tests for the enterprise/ROI relevance scoring."""

from __future__ import annotations

import unittest

from news_pipeline import push_to_artifact
from news_pipeline.score import attach_enterprise_scores, enterprise_score_item

ROI_TEXT = (
    "Enterprise deployment guide: moving agents to production with cost savings, "
    "lower latency, compliance and governance guardrails, backed by a customer case study."
)


class EnterpriseScoreTests(unittest.TestCase):
    def test_enterprise_score_rewards_roi_signals(self) -> None:
        item = {"title": "Production LLM rollout", "raw_content": ROI_TEXT, "tags": []}

        score = enterprise_score_item(item)

        self.assertGreaterEqual(score, 60)
        self.assertEqual(
            set(item["metadata"]["enterprise_signal_components"]),
            {"adoption", "efficiency", "governance", "evidence"},
        )

    def test_enterprise_score_ignores_purely_academic_items(self) -> None:
        item = {
            "title": "A novel attention mechanism",
            "raw_content": "We propose a new attention variant with improved theoretical convergence.",
            "tags": [],
        }

        self.assertEqual(enterprise_score_item(item), 0)

    def test_enterprise_score_taxonomy_bonus_and_cap(self) -> None:
        bare = {"title": "Production deployment", "raw_content": "", "tags": []}
        tagged = {
            "title": "Production deployment",
            "raw_content": "",
            "tags": [],
            "metadata": {"domain": "Enterprise and Knowledge Work"},
        }
        saturated = {"title": "Saturated", "raw_content": ROI_TEXT * 3, "tags": []}

        self.assertEqual(enterprise_score_item(tagged) - enterprise_score_item(bare), 10)
        self.assertLessEqual(enterprise_score_item(saturated), 100)

    def test_dashboard_payload_exposes_enterprise_score(self) -> None:
        items = [
            {
                "source_type": "paper",
                "title": "Serving LLMs in production",
                "raw_content": ROI_TEXT,
                "metadata": {"research_score": 80},
            },
            {
                "source_type": "github",
                "title": "org/enterprise-tool",
                "raw_content": "An AI deployment and observability tool.",
                "metadata": {"item_kind": "repo", "traction_score": 90},
            },
        ]
        attach_enterprise_scores(items)

        payload = push_to_artifact.build_dashboard_payload(items)

        self.assertGreater(payload["papers"][0]["enterpriseScore"], 0)
        self.assertIn("enterpriseSignals", payload["papers"][0])
        self.assertGreater(payload["repos"][0]["enterpriseScore"], 0)

    def test_dashboard_payload_defaults_missing_enterprise_score_to_zero(self) -> None:
        payload = push_to_artifact.build_dashboard_payload(
            [
                {
                    "source_type": "github",
                    "title": "org/plain-repo",
                    "raw_content": "An AI tool.",
                    "metadata": {"item_kind": "repo", "traction_score": 50},
                }
            ]
        )

        self.assertEqual(payload["repos"][0]["enterpriseScore"], 0)


if __name__ == "__main__":
    unittest.main()
