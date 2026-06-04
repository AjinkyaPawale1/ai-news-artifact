from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import requests

from news_pipeline.agents.fetch_papers import fetch_papers, update_last_diagnostics
from news_pipeline.agents.paper_graph import enrich_paper_item
from news_pipeline.agents import paper_graph
from news_pipeline.paper_summarize import (
    enrich_paper_action_items,
    enrich_paper_summaries,
    get_last_action_diagnostics,
    get_last_summary_diagnostics,
)
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
        self.assertEqual(metadata["capability"], "RAG and Knowledge Systems")
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
        self.assertEqual(payload["papers"][0]["priority"], "READ")
        self.assertEqual(len(payload["papers"][0]["actionItems"]), 3)
        self.assertTrue(all(isinstance(action, str) for action in payload["papers"][0]["actionItems"]))
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
        self.assertEqual(payload["actionItems"][0]["priority"], "EXPERIMENT")
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
        self.assertEqual(len(payload["papers"][0]["actionItems"]), 3)
        self.assertTrue(all(isinstance(action, str) for action in payload["papers"][0]["actionItems"]))

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
        self.assertEqual(get_last_summary_diagnostics()["skip_reason"], "missing_api_key")

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_summary_uses_openai_three_bullet_response(self, _mock_sleep: Mock, mock_post: Mock) -> None:
        paper = enrich_paper_item(_paper("paper-openai", "AI Evaluation", "An abstract.")).to_dict()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"output_text": '{"bullets":["Contribution","Evidence","Implication"]}'}
        mock_post.return_value = response

        enrich_paper_summaries([paper])

        self.assertEqual(paper["metadata"]["takeaways"], ["Contribution", "Evidence", "Implication"])
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(get_last_summary_diagnostics()["successes"], 1)

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_actions_use_openai_three_action_response(self, _mock_sleep: Mock, mock_post: Mock) -> None:
        paper = enrich_paper_item(
            _paper("paper-action-openai", "AI Evaluation", "An evaluation benchmark with deployment evidence.")
        ).to_dict()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "output_text": (
                '{"actions":['
                '"Review the benchmark design and evidence assumptions.",'
                '"Run a small comparison against the current evaluation set.",'
                '"Ask whether data coverage or governance limits adoption."'
                "]}"
            )
        }
        mock_post.return_value = response

        enrich_paper_action_items([paper])

        self.assertEqual(
            paper["metadata"]["action_items"],
            [
                "Review the benchmark design and evidence assumptions.",
                "Run a small comparison against the current evaluation set.",
                "Ask whether data coverage or governance limits adoption.",
            ],
        )
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(get_last_action_diagnostics()["successes"], 1)

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_actions_invalid_response_falls_back(self, _mock_sleep: Mock, mock_post: Mock) -> None:
        paper = enrich_paper_item(
            _paper(
                "paper-action-invalid",
                "AI Evaluation",
                "First sentence. Second sentence. Third sentence.",
            )
        ).to_dict()
        original_actions = list(paper["metadata"]["action_items"])
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"output_text": '{"actions":["same","same"]}'}
        mock_post.return_value = response

        enrich_paper_action_items([paper])
        diagnostics = get_last_action_diagnostics()

        self.assertEqual(paper["metadata"]["action_items"], original_actions)
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(diagnostics["retry_count"], 2)
        self.assertEqual(diagnostics["fallbacks"], 1)

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_paper_actions_missing_key_uses_deterministic_fallback(self) -> None:
        paper = enrich_paper_item(
            _paper("paper-action-missing-key", "AI Evaluation", "An evaluation benchmark.")
        ).to_dict()
        original_actions = list(paper["metadata"]["action_items"])

        enrich_paper_action_items([paper])
        diagnostics = get_last_action_diagnostics()

        self.assertEqual(paper["metadata"]["action_items"], original_actions)
        self.assertEqual(len(paper["metadata"]["action_items"]), 3)
        self.assertEqual(diagnostics["skip_reason"], "missing_api_key")
        self.assertEqual(diagnostics["fallbacks"], 1)

    @patch("news_pipeline.agents.fetch_papers.ARXIV_CATEGORIES", ["cs.AI", "cs.CL"])
    @patch("news_pipeline.agents.paper_graph._pace_arxiv_request")
    @patch("news_pipeline.retry.time.sleep")
    @patch("news_pipeline.agents.paper_graph.requests.get")
    def test_fetch_papers_keeps_partial_results_and_diagnostics(
        self, mock_get: Mock, _mock_sleep: Mock, _mock_pace: Mock
    ) -> None:
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
        mock_get.side_effect = [successful, limited, limited, limited]

        papers = fetch_papers()
        diagnostics = update_last_diagnostics(deduplicated_count=1, displayed_count=1)

        self.assertEqual(len(papers), 1)
        self.assertEqual(diagnostics["raw_count"], 1)
        self.assertEqual(diagnostics["seven_day_count"], 1)
        self.assertEqual(diagnostics["deduplicated_count"], 1)
        self.assertEqual(diagnostics["displayed_count"], 1)
        self.assertEqual(diagnostics["categories"][0]["status"], "ok")
        self.assertEqual(diagnostics["categories"][1]["status"], "error")
        self.assertEqual(diagnostics["request_attempts"], 4)
        self.assertEqual(diagnostics["retry_count"], 2)

    @patch("news_pipeline.agents.fetch_papers.ARXIV_CATEGORIES", ["cs.AI"])
    @patch("news_pipeline.agents.paper_graph._pace_arxiv_request")
    @patch("news_pipeline.agents.paper_graph.requests.get")
    def test_fetch_papers_backfills_from_fourteen_days_only_when_needed(
        self, mock_get: Mock, _mock_pace: Mock
    ) -> None:
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

    def test_domain_labels_reject_generic_learning_signal(self) -> None:
        metadata = enrich_paper_item(
            _paper(
                "paper-policy",
                "Policy and World Modeling Co-Training for Language Agents",
                "Reinforcement learning improves language model agents. We propose a framework for on-policy training.",
            )
        ).metadata

        self.assertEqual(metadata["domain"], "Other")

    def test_domain_labels_detect_clinical_paper(self) -> None:
        metadata = enrich_paper_item(
            _paper(
                "paper-clinical",
                "Towards Multidisciplinary Summarization of Hospital Stays",
                "A clinical provenance pipeline for multidisciplinary NICU hospital notes.",
            )
        ).metadata

        self.assertEqual(metadata["domain"], "Healthcare and Life Sciences")

    def test_multimodal_capability_and_robotics_domain_win_for_maser(self) -> None:
        metadata = enrich_paper_item(
            _paper(
                "paper-maser",
                "MASER: Modality-Adaptive Specialist Routing for Embodied 3D Spatial Intelligence",
                "A vision-language model uses multimodal adapters for embodied spatial intelligence evaluation.",
            )
        ).metadata

        self.assertEqual(metadata["capability"], "Multimodal AI")
        self.assertEqual(metadata["domain"], "Robotics and Autonomous Systems")

    @patch("news_pipeline.agents.fetch_papers.ARXIV_CATEGORIES", ["cs.AI"])
    @patch("news_pipeline.agents.paper_graph._pace_arxiv_request")
    @patch("news_pipeline.retry.time.sleep")
    @patch("news_pipeline.agents.paper_graph.requests.get")
    def test_fetch_papers_retries_transient_arxiv_failure(
        self, mock_get: Mock, _mock_sleep: Mock, _mock_pace: Mock
    ) -> None:
        published = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        xml = (
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            f"<entry><title>Recent AI Benchmark</title><summary>AI benchmark.</summary>"
            f"<published>{published}</published><id>https://arxiv.org/abs/retry-success</id></entry></feed>"
        )
        failed = Mock()
        failed.raise_for_status.side_effect = requests.ConnectionError("temporary")
        successful = Mock(text=xml)
        successful.raise_for_status.return_value = None
        mock_get.side_effect = [failed, successful]

        papers = fetch_papers()
        diagnostics = update_last_diagnostics(deduplicated_count=len(papers), displayed_count=len(papers))

        self.assertEqual(len(papers), 1)
        self.assertEqual(diagnostics["request_attempts"], 2)
        self.assertEqual(diagnostics["retry_count"], 1)

    @patch("news_pipeline.agents.fetch_papers.ARXIV_CATEGORIES", ["cs.AI"])
    @patch("news_pipeline.agents.paper_graph._pace_arxiv_request")
    @patch("news_pipeline.retry.time.sleep")
    @patch("news_pipeline.agents.paper_graph.requests.get")
    def test_fetch_papers_retries_malformed_xml(
        self, mock_get: Mock, _mock_sleep: Mock, _mock_pace: Mock
    ) -> None:
        published = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        malformed = Mock(text="<feed>")
        malformed.raise_for_status.return_value = None
        successful = Mock(
            text=(
                '<feed xmlns="http://www.w3.org/2005/Atom">'
                f"<entry><title>Recovered</title><summary>AI benchmark.</summary>"
                f"<published>{published}</published><id>https://arxiv.org/abs/xml-retry</id></entry></feed>"
            )
        )
        successful.raise_for_status.return_value = None
        mock_get.side_effect = [malformed, successful]

        papers = fetch_papers()
        diagnostics = update_last_diagnostics(deduplicated_count=len(papers), displayed_count=len(papers))

        self.assertEqual(len(papers), 1)
        self.assertEqual(diagnostics["retry_count"], 1)

    @patch("news_pipeline.agents.paper_graph.ARXIV_REQUEST_INTERVAL_SECONDS", 3)
    @patch("news_pipeline.agents.paper_graph.time.sleep")
    @patch("news_pipeline.agents.paper_graph.time.monotonic", side_effect=[10.0, 11.0, 13.0])
    def test_arxiv_pacing_waits_between_requests(self, mock_monotonic: Mock, mock_sleep: Mock) -> None:
        with patch.object(paper_graph, "_LAST_ARXIV_REQUEST_AT", None):
            paper_graph._pace_arxiv_request()
            paper_graph._pace_arxiv_request()

        self.assertEqual(mock_monotonic.call_count, 3)
        mock_sleep.assert_called_once_with(2.0)

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_summary_retries_invalid_json_then_succeeds(self, _mock_sleep: Mock, mock_post: Mock) -> None:
        paper = enrich_paper_item(_paper("paper-retry", "AI Evaluation", "An abstract.")).to_dict()
        invalid = Mock()
        invalid.raise_for_status.return_value = None
        invalid.json.return_value = {"output_text": "not-json"}
        successful = Mock()
        successful.raise_for_status.return_value = None
        successful.json.return_value = {"output_text": '{"bullets":["Contribution","Evidence","Implication"]}'}
        mock_post.side_effect = [invalid, successful]

        enrich_paper_summaries([paper])
        diagnostics = get_last_summary_diagnostics()

        self.assertEqual(paper["metadata"]["takeaways"], ["Contribution", "Evidence", "Implication"])
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(diagnostics["retry_count"], 1)
        self.assertEqual(diagnostics["successes"], 1)

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_summary_retries_invalid_bullet_shape_then_succeeds(
        self, _mock_sleep: Mock, mock_post: Mock
    ) -> None:
        paper = enrich_paper_item(_paper("paper-schema-retry", "AI Evaluation", "An abstract.")).to_dict()
        invalid = Mock()
        invalid.raise_for_status.return_value = None
        invalid.json.return_value = {"output_text": '{"bullets":"abc"}'}
        successful = Mock()
        successful.raise_for_status.return_value = None
        successful.json.return_value = {"output_text": '{"bullets":["Contribution","Evidence","Implication"]}'}
        mock_post.side_effect = [invalid, successful]

        enrich_paper_summaries([paper])
        diagnostics = get_last_summary_diagnostics()

        self.assertEqual(paper["metadata"]["takeaways"], ["Contribution", "Evidence", "Implication"])
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(diagnostics["retry_count"], 1)
        self.assertEqual(diagnostics["successes"], 1)

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_summary_exhausts_retries_then_falls_back(self, _mock_sleep: Mock, mock_post: Mock) -> None:
        paper = enrich_paper_item(
            _paper("paper-fallback", "AI Evaluation", "First sentence. Second sentence. Third sentence.")
        ).to_dict()
        mock_post.side_effect = requests.ConnectionError("temporary")

        enrich_paper_summaries([paper])
        diagnostics = get_last_summary_diagnostics()

        self.assertEqual(paper["metadata"]["takeaways"], ["First sentence.", "Second sentence.", "Third sentence."])
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(diagnostics["retry_count"], 2)
        self.assertEqual(diagnostics["fallbacks"], 1)

    @patch("news_pipeline.paper_summarize.requests.post")
    @patch("news_pipeline.retry.time.sleep")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_paper_summary_disables_run_for_insufficient_quota(self, _mock_sleep: Mock, mock_post: Mock) -> None:
        first = enrich_paper_item(_paper("paper-quota", "AI Evaluation", "First abstract.")).to_dict()
        second = enrich_paper_item(_paper("paper-quota-2", "AI Evaluation", "Second abstract.")).to_dict()
        response = Mock(status_code=429)
        response.json.return_value = {"error": {"code": "insufficient_quota"}}
        error = requests.HTTPError("quota", response=response)
        failed = Mock()
        failed.raise_for_status.side_effect = error
        mock_post.return_value = failed

        enrich_paper_summaries([first, second])
        diagnostics = get_last_summary_diagnostics()

        self.assertEqual(mock_post.call_count, 1)
        self.assertTrue(diagnostics["disabled"])
        self.assertEqual(diagnostics["skip_reason"], "insufficient_quota")
        self.assertEqual(diagnostics["fallbacks"], 2)


if __name__ == "__main__":
    unittest.main()
