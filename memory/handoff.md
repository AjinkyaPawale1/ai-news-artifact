# Handoff Notes

Last updated: 2026-06-02
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
- Added a LangGraph-style model/tool release extraction workflow for RSS-style sources.
- Wired `model` and `tool_service` items through the pipeline artifact into `models` and `toolsServices`.
- Adjusted exact-URL dedupe to prefer model/tool classifications over duplicate generic RSS entries.
- Added bounded dynamic model/tool discovery: protected core feeds, rotating emerging feeds/terms, and optional LLM classification for candidate releases.
- Added model/tools OpenAI quota diagnostics and a guard that skips later LLM classifier calls after quota/auth failures.
- Expanded model/tool provider coverage with official OpenAI, Google, Microsoft, NVIDIA, AWS, Hugging Face, GitHub, Anthropic, Meta, Mistral, and Cohere sources.
- Added official source-page extraction for providers without reliable RSS, enriched source-page candidates with article excerpts, and added dashboard release/source links for model and tool cards.
- Tightened model/tool release date resolution by extracting article publish dates from HTML metadata, URL patterns, and fallback headers, then dropping undated or stale entries outside the active weekly window.
- Changed model and tool sections from always-expanded cards to repo-style collapsed rows that expand on click to show the full summary and release/source links.
- Added `docs/model-tools-agent-architecture.md` documenting the end-to-end model/tools workflow: dynamic input resolution, LangGraph stages, date gating, artifact mapping, supervisor integration, diagnostics, and frontend rendering.
- Centralized human-maintained model/tools source groups, classifier terms, and limits in `news_pipeline.model_tools_config`.
- Removed the redundant model/tools feed fallback layer and made normal runs resolve deduplicated core plus emerging feeds.
- Reused `MODEL_TOOL_MAX_ITEMS` for both graph selection and dashboard release-card rendering.
- Added focused model/tools tests for bounded rotation, feed composition, and the shared output cap.
- Clarified the model/tools architecture document with the two distinct optional OpenAI paths: one emerging-source proposal call per run and up to 24 per-candidate classification refinement calls.
- Created a new private GitHub remote at `https://github.com/AjinkyaPawale1/llm-news-artifact`, committed the current local workspace state, pushed the active and existing local branches, and reset the remote default branch to `main`.
- Added deterministic paper action extraction with LangGraph fallback semantics.
- Wired paper metadata into dashboard paper cards and top action items.
- Added focused unittest coverage for paper action metadata and artifact mapping.
- Replaced FSO-specific paper enrichment with generic AI/ML capability and domain taxonomies.
- Added deterministic paper `research_score` components, visible research signals, and independent top-eight paper ranking.
- Added a generic `action_score` retained for paper action metadata.
- Made arXiv extraction preserve partial category results and emit paper diagnostics.
- Updated the paper dashboard card to show generic tags, `RESEARCH SCORE`, and research signals.
- Added `npm run pipeline:papers` for paper-only refreshes that preserve existing non-paper dashboard sections.
- Added seven-day-first paper selection with days 8-14 used only to fill missing top-eight slots.
- Added optional OpenAI Responses API paper summaries with exactly three abstract-grounded bullets and a deterministic fallback when no key is configured.
- Reduced paper tags to capability plus domain and added a yellow `OPEN PAPER` link.
- Replaced the weekly briefing's mixed action-card section with paper-only ranked cards labeled `RESEARCH PAPERS`; repos, releases, and tools remain separate.
- Added `docs/research-paper-agent-architecture.md` documenting the end-to-end paper workflow: arXiv extraction, freshness backfill, LangGraph state, deterministic scoring, optional OpenAI summaries, fallbacks, diagnostics, paper-only refresh, artifact mapping, and frontend payload.
- Refactored the paper workflow into explicit LangGraph fetch, recent-selection, and metadata-enrichment stages with sequential fallback.
- Added paced arXiv category requests, two transient retries with exponential backoff and jitter, and request/retry health diagnostics.
- Made OpenAI paper summaries the default when a key exists, added two transient retries, and recorded summary attempts, retries, successes, fallbacks, and disable reasons.
- Tightened deterministic paper labels with weighted phrase matching, word boundaries, overlap suppression, and `Other` for weak or tied domains.
- Added visible paper priority chips and expanded-card `RECOMMENDED ACTIONS`.

## Current State
- Project runs via Vite from `apps/web` using root npm scripts.
- Python pipeline fetches real arXiv, GitHub, and RSS items and writes `data/output.json`.
- GitHub repo bullets are generated deterministically by default and can use OpenAI when `OPENAI_API_KEY` is set.
- Dashboard reads generated JSON data and builds successfully.
- Generated health log is written to `data/health.json`.
- Agent operating guidance is now centralized in `AGENTS.md`.
- Repo memory now includes context, decisions, handoff, tasks, and errors.
- The dashboard can now receive generated model release and AI tool/service cards with longer notes plus release/source links when current feed entries match deterministic and/or LLM classification.
- Model/tool dynamic state is persisted in `data/model_tools_dynamic_config.json`; health output includes extraction diagnostics and dynamic refresh metadata.
- `data/model_tools_dynamic_config.json` is generated inspectable state, not the primary contributor edit point; static defaults live in `apps/pipeline/src/news_pipeline/model_tools_config.py`.
- Latest refresh produced 1 model card and 6 tool/service cards, all with resolved in-window dates and no `Unknown` values.
- The docs folder now includes separate architecture pages for research papers, GitHub discovery, and model/tool release discovery.
- `origin` now points to `https://github.com/AjinkyaPawale1/llm-news-artifact.git`.
- Remote branch currently published: `main`.

## Next Recommended Actions
1. Day 2: Improve dedup.py with fuzzy title matching and related_links.
2. Day 2: Strengthen normalize.py validation and score.py relevance scoring.
3. Add cross-source repo mention extraction so RSS/arXiv GitHub links influence traction scoring.
4. Day 3: Implement stronger quality gate and final dashboard section mapping.
5. Add screenshots to README when the dashboard UI stabilizes.
6. Use `memory/errors.md` when repeated failed approaches or useful debugging lessons appear.
7. Review `data/model_tools_dynamic_config.json` after live weekly runs and tune candidate feeds if the LLM proposal repeatedly keeps low-yield sources.
8. Watch source-page cards for sparse/generic vendor site copy; if this recurs, add provider-specific content extraction rules before increasing card count.
9. Consider widening source coverage only if weekly model-card volume stays too low after the stricter date gate; do not relax the recent-date requirement without another filtering strategy.
10. Consider extracting GitHub/code links from arXiv abstracts or paper pages so `has_code` can be based on explicit links instead of text signals.

## Risks / Watchouts
- If utility classes expand, CDN-based styling may be less maintainable than local Tailwind setup.
- GitHub API runs unauthenticated unless GITHUB_TOKEN is provided; rate limits may apply.
- LangGraph is now a pipeline dependency; run `pip install -r apps/pipeline/requirements.txt` after pulling.
- OpenAI repo summaries are optional and require `OPENAI_API_KEY`; `OPENAI_MODEL` defaults to `gpt-5.4-mini`.
- Some RSS feeds may fail or return sparse content; health log captures source-level status.
- Model/tool extraction remains deterministic-first, but official source pages can pass release-signal checks and may rely on LLM classification for final card naming and notes.
- The model/tool workflow now drops entries when a recent publish date cannot be resolved; this avoids `Unknown` cards and stale releases, but it can reduce weekly card count when provider pages omit publish metadata.
- Optional model/tool LLM behavior is bounded: it proposes emerging feed/keyword rotations from a candidate catalog and classifies only limited candidate entries.
- `429 insufficient_quota` from OpenAI is an API billing/quota issue, not a normal transient rate limit; see `memory/errors.md` before retry loops.
- Root `data/output.json` is a shared interface; keep pipeline-owned writes and frontend reads separate.
- Paper research metadata and scores are deterministic keyword logic; adjust keyword groups and score weights carefully if dashboard labels or ranking feel too broad or too narrow.
- arXiv runs intentionally add three-second spacing between category requests to reduce avoidable `429` responses.
- If installed binaries hang on macOS, clear quarantine metadata from `node_modules` with `xattr -dr com.apple.quarantine node_modules`.
- Keep `AGENTS.md` and the `memory/` files in sync when agent operating rules change.
- This checkout is a git worktree; GitHub CLI repository creation works more reliably by creating the remote first, then adding `origin`, rather than using `gh repo create --source=.`.

## Quick Resume Steps
- npm install
- pip install -r apps/pipeline/requirements.txt
- npm run pipeline
- npm run dev
- Open local URL shown by Vite
- Read `AGENTS.md` plus relevant files under `memory/` before new implementation work.
