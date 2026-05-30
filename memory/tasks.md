# Task Board

Last updated: 2026-05-28

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
- [x] Add model release and AI tool/service extraction from RSS-style sources.
- [x] Wire generated model/tool release cards into `data/output.json`.
- [x] Add bounded LLM-assisted emerging feed and keyword refresh for model/tool releases.
- [x] Add optional LLM classification for bounded model/tool release candidates.
- [x] Expand official model/tool provider feeds and source pages.
- [x] Add richer model/tool card summaries and release/source links.
- [x] Enforce recent-dated model/tool cards and make them collapsed/expandable like repo cards.
- [x] Add end-to-end model/tools agent architecture documentation under `docs/`.

## Todo
- [ ] Day 2: Implement fuzzy deduplication and related links.
- [ ] Day 2: Improve normalization validation.
- [ ] Day 2: Improve scoring dimensions and weights.
- [ ] Day 3: Strengthen quality gate and dashboard mapping.
- [ ] Add README screenshots when the dashboard UI stabilizes.
- [ ] Add CI for build validation.
- [ ] Consider migrating from Tailwind CDN to local Tailwind pipeline.
- [ ] Add cross-source repo mention extraction from RSS and arXiv links.
- [ ] Review model/tool dynamic config after weekly runs and adjust candidate feeds if needed.
- [ ] Add provider-specific article extraction rules if source-page cards show repeated generic vendor copy.

## In Progress
- [ ] None

## Blocked
- [ ] None
