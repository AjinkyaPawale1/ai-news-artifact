# Handoff Notes

Last updated: 2026-05-28
Owner: AI agent (Codex)

## Completed
- Established standalone git repo for this project directory.
- Created and pushed GitHub remote repository.
- Added runtime scaffolding to execute the dashboard component locally.
- Added repository memory management framework (agent.md + memory folder).
- Implemented Day 1 Python agent pipeline scaffold.
- Added arXiv, GitHub, and RSS fetch agents.
- Added supervisor fan-out with ThreadPoolExecutor and source health logging.
- Added data/output.json generation and wired the React dashboard to import it.
- Added npm run pipeline wrapper.
- Validated npm run pipeline, python compileall, ruff check, and npm run build.
- Restructured into Monorepo Lite layout with `apps/web` and `apps/pipeline`.
- Converted pipeline imports to package-relative imports under `news_pipeline`.
- Added `docs/architecture.md`.
- Added Rollup WASM package alias so Vite builds avoid native Rollup addon issues on this machine.
- Refreshed `IMPLEMENTATION_PLAN.md` to match the Monorepo Lite structure.
- Added top-level `README.md` for normal project onboarding.
- Added a LangGraph-based GitHub repository discovery workflow.
- Added richer repo metadata, bullets, traction scores, release links, and expandable frontend repo cards.
- Renamed `agent.md` to `AGENTS.md` and expanded it with Karpathy-style coding rules, X-thread memory practices, approval gates, and repo-specific permanent facts.
- Added `memory/errors.md` for repeated failures and troubleshooting lessons.
- Added deterministic paper action extraction with LangGraph fallback semantics.
- Wired paper metadata into dashboard paper cards and top action items.
- Added focused unittest coverage for paper action metadata and artifact mapping.

## Current State
- Project runs via Vite from `apps/web` using root npm scripts.
- Python pipeline fetches real arXiv, GitHub, and RSS items and writes `data/output.json`.
- GitHub repo bullets are generated deterministically by default and can use OpenAI when `OPENAI_API_KEY` is set.
- arXiv paper items carry deterministic `metadata` for priority, takeaways, action items,
  relevance, verticals, and code availability.
- Dashboard reads generated JSON data and builds successfully.
- Generated health log is written to `data/health.json`.
- Agent operating guidance is now centralized in `AGENTS.md`.
- Repo memory now includes context, decisions, handoff, tasks, and errors.

## Next Recommended Actions
1. Day 2: Improve dedup.py with fuzzy title matching and related_links.
2. Day 2: Strengthen normalize.py validation and score.py relevance scoring.
3. Add cross-source repo mention extraction so RSS/arXiv GitHub links influence traction scoring.
4. Day 3: Implement stronger quality gate and final dashboard section mapping.
5. Add screenshots to README when the dashboard UI stabilizes.
6. Use `memory/errors.md` when repeated failed approaches or useful debugging lessons appear.
7. Consider extracting GitHub/code links from arXiv abstracts or paper pages so `has_code`
   can be based on explicit links instead of text signals.

## Risks / Watchouts
- If utility classes expand, CDN-based styling may be less maintainable than local Tailwind setup.
- GitHub API runs unauthenticated unless GITHUB_TOKEN is provided; rate limits may apply.
- LangGraph is now a pipeline dependency; run `pip install -r apps/pipeline/requirements.txt` after pulling.
- OpenAI repo summaries are optional and require `OPENAI_API_KEY`; `OPENAI_MODEL` defaults to `gpt-5.4-mini`.
- Some RSS feeds may fail or return sparse content; health log captures source-level status.
- Root `data/output.json` is a shared interface; keep pipeline-owned writes and frontend reads separate.
- Paper action metadata is deterministic keyword logic; adjust keyword groups carefully if
  dashboard labels start feeling too broad or too narrow.
- If installed binaries hang on macOS, clear quarantine metadata from `node_modules` with `xattr -dr com.apple.quarantine node_modules`.
- Keep `AGENTS.md` and the `memory/` files in sync when agent operating rules change.

## Quick Resume Steps
- npm install
- pip install -r apps/pipeline/requirements.txt
- npm run pipeline
- npm run dev
- Open local URL shown by Vite
- Read `AGENTS.md` plus relevant files under `memory/` before new implementation work.
