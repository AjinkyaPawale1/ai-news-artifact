# Task Board

Last updated: 2026-06-01

## Done
- [x] Make JSX dashboard runnable with React + Vite.
- [x] Create and push GitHub repository.
- [x] Add repository-level agent and memory documentation.
- [x] Create Python pipeline scaffold.
- [x] Implement Day 1 fetch agents for arXiv, GitHub, and RSS.
- [x] Generate data/output.json and data/health.json from pipeline.
- [x] Wire dashboard to generated JSON artifact.
- [x] Add npm run pipeline wrapper.
- [x] Restructure repo into Monorepo Lite layout.
- [x] Document architecture in docs/architecture.md.
- [x] Refresh IMPLEMENTATION_PLAN.md for the new structure.
- [x] Add top-level README.md.
- [x] Replace GitHub fetch internals with a LangGraph repo discovery workflow.
- [x] Add richer GitHub repo artifact fields and expandable frontend repo cards.
- [x] Rename `agent.md` to `AGENTS.md` and expand agent operating guidance.
- [x] Add `memory/errors.md` for repeated failures and troubleshooting lessons.
- [x] Add deterministic arXiv paper action metadata and artifact mapping.
- [x] Add focused tests for paper action extraction.
- [x] Replace FSO-specific paper enrichment with generic AI/ML metadata.
- [x] Add independent deterministic paper research ranking and top-eight artifact mapping.
- [x] Preserve partial arXiv category results and publish paper fetch diagnostics.
- [x] Keep the retained paper action metadata scoring generic.
- [x] Add a paper-only refresh command that preserves non-paper dashboard sections.
- [x] Add seven-day-first paper selection with bounded fourteen-day backfill.
- [x] Add optional OpenAI paper summaries with deterministic three-bullet fallback.
- [x] Reduce paper-card tags and add a highlighted paper link.
- [x] Replace the weekly briefing mixed action queue with paper-only research cards.

## Todo
- [ ] Day 2: Implement fuzzy deduplication and related links.
- [ ] Day 2: Improve normalization validation.
- [ ] Day 2: Improve scoring dimensions and weights.
- [ ] Day 3: Strengthen quality gate and dashboard mapping.
- [ ] Add README screenshots when the dashboard UI stabilizes.
- [ ] Add CI for build validation.
- [ ] Consider migrating from Tailwind CDN to local Tailwind pipeline.
- [ ] Add cross-source repo mention extraction from RSS and arXiv links.
- [ ] Improve paper `has_code` by extracting explicit repository/code links from arXiv metadata or paper pages.

## In Progress
- [ ] None

## Blocked
- [ ] None
