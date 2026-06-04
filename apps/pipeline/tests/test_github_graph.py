"""Focused tests for deterministic GitHub repository labels."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from news_pipeline.agents.github_graph import _best_for_label, _fallback_repo_actions, _repo_to_item


class GitHubClassificationTests(unittest.TestCase):
    def test_repo_action_fallback_returns_three_experiment_steps(self) -> None:
        actions = _fallback_repo_actions(
            {
                "full_name": "example/agent-lab",
                "description": "Agent workflow framework.",
                "language": "Python",
                "latest_release": {"tag_name": "v1.2.0"},
            },
            "AI Agent Apps",
        )

        self.assertEqual(len(actions), 3)
        self.assertIn("example/agent-lab", actions[0])
        self.assertIn("AI agent apps".lower(), actions[1])
        self.assertIn("v1.2.0", actions[2])

    @patch("news_pipeline.agents.github_graph._openai_repo_brief")
    def test_repo_item_uses_llm_actions_when_available(self, mock_brief) -> None:
        mock_brief.return_value = {
            "desc": "LLM-generated repo summary.",
            "bullets": ["Summarize setup.", "Identify integration points.", "Track maintenance signal."],
            "action_items": ["Run the sample app.", "Benchmark one agent task.", "Review deployment gaps."],
            "why_trending": "Recently active.",
        }

        item = _repo_to_item(
            {
                "full_name": "example/agent-lab",
                "html_url": "https://github.com/example/agent-lab",
                "description": "Agent workflow framework.",
                "language": "Python",
                "stargazers_count": 100,
                "latest_release": {"tag_name": "v1.2.0", "html_url": "https://example.com/release"},
                "owner": {"login": "example"},
            }
        )

        self.assertEqual(item.metadata["action_items"], ["Run the sample app.", "Benchmark one agent task.", "Review deployment gaps."])
        self.assertEqual(item.metadata["bullets"][0], "Summarize setup.")

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_repo_item_falls_back_to_three_actions_without_llm(self) -> None:
        item = _repo_to_item(
            {
                "full_name": "example/mcp-tools",
                "html_url": "https://github.com/example/mcp-tools",
                "description": "MCP server toolkit.",
                "language": "TypeScript",
                "topics": ["mcp", "agents"],
                "latest_release": {},
                "owner": {"login": "example"},
            }
        )

        self.assertEqual(len(item.metadata["action_items"]), 3)
        self.assertIn("example/mcp-tools", item.metadata["action_items"][0])

    def test_knowledge_product_is_not_flattened_into_rag_infrastructure(self) -> None:
        label = _best_for_label(
            {
                "full_name": "AgriciDaniel/claude-obsidian",
                "description": "Obsidian plugin that turns sources into a Markdown knowledge graph and second brain.",
                "topics": ["pkm", "wiki"],
            }
        )

        self.assertEqual(label, "Knowledge Management")

    def test_rag_infrastructure_requires_retrieval_specific_signals(self) -> None:
        label = _best_for_label(
            {
                "full_name": "example/rag-pipeline",
                "description": "RAG retrieval service with vector embeddings and document chunking.",
            }
        )

        self.assertEqual(label, "RAG Infrastructure")

    def test_generic_context_term_does_not_imply_rag_infrastructure(self) -> None:
        label = _best_for_label(
            {
                "full_name": "example/prompt-context-helper",
                "description": "Small context helper for AI prompts.",
            }
        )

        self.assertEqual(label, "AI Engineering")


if __name__ == "__main__":
    unittest.main()
