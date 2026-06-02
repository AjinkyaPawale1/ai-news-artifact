"""Focused tests for deterministic GitHub repository labels."""

from __future__ import annotations

import unittest

from news_pipeline.agents.github_graph import _best_for_label


class GitHubClassificationTests(unittest.TestCase):
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
