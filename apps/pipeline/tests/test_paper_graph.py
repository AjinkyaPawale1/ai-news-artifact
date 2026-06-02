from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import requests

from news_pipeline.agents.fetch_papers import fetch_papers, update_last_diagnostics
from news_pipeline.agents.paper_graph import enrich_paper_item
from news_pipeline.paper_summarize import enrich_paper_summaries
from news_pipeline.push_to_artifact import build_dashboard_payload, update_papers_in_payload
from news_pipeline.schema import Item
from news_pipeline.score import attach_action_scores


def _paper(
    paper_id: str,
    title: str,
    raw_content: str,
    *,
    published_date: str | None = None,
) -> Item:
    return Item(
        id=paper_id,
        source="arXiv",
        source_type="paper",
        title=title,
        url=f"https://arxiv.org/pdf/{paper_id}",
        published_date=published_date or datetime.now(timezone.utc).isoformat(),
        raw_content=raw_content,
        tags=["cs.AI"],
    )


class PaperGraphTests(unittest.TestCase):
    def test_enrich_paper_item_adds_generic_metadata_and_score(self) -> None:
        paper = _paper(
            "paper-1",
            "Agentic RAG for Enterprise Knowledge Workflows",
            (
                "We introduce an open-source agent framework with a GitHub implementation "
                "and benchmark dataset for retrieval augmented generation in enterprise workflows."
            ),
        )

        metadata = enrich_paper_item(paper).metadata

        self.assertEqual(metadata["priority"], "EXPERIMENT")
        self.assertEqual(metadata["capability"], "Agentic AI")
        self.assertEqual(metadata["domain"], "Enterprise and Knowledge Work")
        self.assertGreater(metadata["research_score"], 0)
        self.assertEqual(set(metadata["research_score_components"]), {
            "topical_fit",
            "evidence",
            "applicability",
            "reproducibility",
            "novelty",
            "recency",
        })
        self.assertEqual(metadata["research_signals"]["reproducibility"], "High")
        self.assertNotIn("relevance", metadata)
        self.assertNotIn("verticals", metadata)
        self.assertTrue(metadata["has_code"])
        self.assertEqual(len(metadata["paper_tags"]), 2)

    def test_enrich_paper_item_uses_generic_fallbacks(self) -> None:
        metadata = enrich_paper_item(_paper("paper-2", "A Specialized Study", "Sparse observations.")).metadata

        self.assertEqual(metadata["capability"], "Other AI/ML")
        self.assertEqual(metadata["domain"], "Other")
        self.assertEqual(metadata["priority"], "READ")

    def test_share_priority_uses_generic_broad_impact_terms(self) -> None:
        metadata = enrich_paper_item(
            _paper("paper-3", "Responsible AI Safety Evaluation", "A governance study for general-purpose AI systems.")
        ).metadata

        self.assertEqual(metadata["priority"], "SHARE")

    def test_dashboard_payload_ranks_and_limits_papers(self) -> None:
        papers = []
        for index in range(10):
            paper = enrich_paper_item(_paper(f"paper-{index}", f"AI benchmark {index}", "AI benchmark evaluation."))
            paper.metadata["research_score"] = index
            record = paper.to_dict()
            record["score"] = 40
            record["action_score"] = index
            papers.append(record)

        payload = build_dashboard_payload(papers)

        self.assertEqual(len(payload["papers"]), 8)
        self.assertEqual(payload["papers"][0]["researchScore"], 9)
        self.assertEqual(payload["papers"][-1]["researchScore"], 2)
        self.assertIn("researchSignals", payload["papers"][0])
        self.assertNotIn("relevance", payload["papers"][0])
        self.assertNotIn("verticals", payload["papers"][0])

    def test_action_items_compatibility_field_uses_papers_only(self) -> None:
        items = [
            {
                "id": "rss-1",
                "source": "RSS",
                "source_type": "rss",
                "title": "General update",
                "url": "https://example.com/general",
                "published_date": datetime.now(timezone.utc).isoformat(),
                "raw_content": "A short general announcement.",
                "tags": [],
                "metadata": {},
            },
            enrich_paper_item(
                _paper(
                    "paper-action",
                    "Production Agent Evaluation Framework",
                    "Open-source AI agent framework with GitHub code, benchmark dataset, evaluation, and deployment workflow.",
                )
            ).to_dict(),
        ]
        attach_action_scores(items)

        payload = build_dashboard_payload(items)

        self.assertEqual(len(payload["actionItems"]), 1)
        self.assertEqual(payload["actionItems"][0]["source"], "arXiv")
        self.assertGreater(items[1]["action_score"], items[0]["action_score"])

    def test_paper_only_payload_refresh_preserves_other_sections(self) -> None:
        paper = enrich_paper_item(_paper("paper-refresh", "AI Evaluation", "AI benchmark evaluation.")).to_dict()
        existing = {
            "generatedAt": "old",
            "stats": [{"label": "PAPERS SCANNED", "value": "0", "sub": "arXiv"}],
            "actionItems": [{"title": "Keep action"}],
            "repos": [{"name": "keep/repo"}],
            "blogs": [{"title": "Keep blog"}],
            "models": [{"name": "Keep model"}],
            "toolsServices": [{"name": "Keep tool"}],
        }
        health = [{"source": "papers", "status": "ok"}]

        payload = update_papers_in_payload(existing, [paper], health)

        self.assertEqual(payload["stats"][0]["value"], "1")
        self.assertEqual(len(payload["papers"]), 1)
        self.assertEqual(payload["repos"], existing["repos"])
        self.assertEqual(payload["blogs"], existing["blogs"])
        self.assertEqual(payload["models"], existing["models"])
        self.assertEqual(payload["toolsServices"], existing["toolsServices"])
        self.assertEqual(len(payload["actionItems"]), 1)
        self.assertEqual(payload["actionItems"][0]["source"], "arXiv")

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_paper_summary_fallback_uses_three_abstract_grounded_bullets(self) -> None:
        paper = enrich_paper_item(
            _paper(
                "paper-summary",
                "AI Evaluation",
                "We introduce a benchmark. It compares three baselines. Results improve evaluation coverage.",
            )
        ).to_dict()

        enrich_paper_summaries([paper])

        self.assertEqual(
            paper["metadata"]["takeaways"],
            ["We introduce a benchmark.", "It compares three baselines.", "Results improve evaluation coverage."],
        )

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_summary_uses_openai_three_bullet_response(self, mock_post: Mock) -> None:
        paper = enrich_paper_item(_paper("paper-openai", "AI Evaluation", "An abstract.")).to_dict()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"output_text": '{"bullets":["Contribution","Evidence","Implication"]}'}
        mock_post.return_value = response

        enrich_paper_summaries([paper])

        self.assertEqual(paper["metadata"]["takeaways"], ["Contribution", "Evidence", "Implication"])
        self.assertEqual(mock_post.call_count, 1)

    @patch("news_pipeline.agents.fetch_papers.ARXIV_CATEGORIES", ["cs.AI", "cs.CL"])
    @patch("news_pipeline.agents.fetch_papers.requests.get")
    def test_fetch_papers_keeps_partial_results_and_diagnostics(self, mock_get: Mock) -> None:
        published = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        xml = f"""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Recent AI Benchmark</title>
            <summary>An AI benchmark evaluation with code.</summary>
            <published>{published}</published>
            <id>https://arxiv.org/abs/2606.00001</id>
            <author><name>A. Researcher</name></author>
            <category term="cs.AI" />
            <link title="pdf" href="https://arxiv.org/pdf/2606.00001" />
          </entry>
        </feed>
        """
        successful = Mock(text=xml)
        successful.raise_for_status.return_value = None
        limited = Mock()
        limited.raise_for_status.side_effect = requests.HTTPError("429 rate limited")
        mock_get.side_effect = [successful, limited]

        papers = fetch_papers()
        diagnostics = update_last_diagnostics(deduplicated_count=1, displayed_count=1)

        self.assertEqual(len(papers), 1)
        self.assertEqual(diagnostics["raw_count"], 1)
        self.assertEqual(diagnostics["seven_day_count"], 1)
        self.assertEqual(diagnostics["deduplicated_count"], 1)
        self.assertEqual(diagnostics["displayed_count"], 1)
        self.assertEqual(diagnostics["categories"][0]["status"], "ok")
        self.assertEqual(diagnostics["categories"][1]["status"], "error")

    @patch("news_pipeline.agents.fetch_papers.ARXIV_CATEGORIES", ["cs.AI"])
    @patch("news_pipeline.agents.fetch_papers.requests.get")
    def test_fetch_papers_backfills_from_fourteen_days_only_when_needed(self, mock_get: Mock) -> None:
        recent = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        older = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat().replace("+00:00", "Z")
        entries = []
        for index in range(5):
            entries.append(
                f"<entry><title>Recent {index}</title><summary>AI benchmark.</summary><published>{recent}</published>"
                f"<id>https://arxiv.org/abs/recent-{index}</id></entry>"
            )
        for index in range(5):
            entries.append(
                f"<entry><title>Backfill {index}</title><summary>AI benchmark.</summary><published>{older}</published>"
                f"<id>https://arxiv.org/abs/backfill-{index}</id></entry>"
            )
        response = Mock(text=f'<feed xmlns="http://www.w3.org/2005/Atom">{"".join(entries)}</feed>')
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        papers = fetch_papers()
        diagnostics = update_last_diagnostics(deduplicated_count=len(papers), displayed_count=min(len(papers), 8))

        self.assertEqual(len(papers), 8)
        self.assertEqual(diagnostics["seven_day_count"], 5)
        self.assertEqual(diagnostics["fourteen_day_count"], 10)
        self.assertEqual(diagnostics["backfill_count"], 3)
        self.assertEqual(diagnostics["selected_window_days"], 14)


if __name__ == "__main__":
    unittest.main()
