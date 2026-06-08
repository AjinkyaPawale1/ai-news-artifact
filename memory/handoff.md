# Handoff Notes

Last updated: 2026-06-08
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
- Replaced financial-services-specific paper enrichment with generic AI/ML capability and domain taxonomies.
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
- Replaced the legacy branded dashboard shell with the neutral `AI Intelligence Brief`.
- Reworked the UI into Weekly Snapshot, Research, Repos, Releases, Signals, and Pipeline
  tabs. The snapshot is concise, Signals is explicitly placeholder-only, and Pipeline
  renders the current multi-source flow plus live health cards.
- Replaced the misleading legacy relevance stat with truthful paper, repo, release, and
  healthy-source snapshot metrics.
- Changed RSS collection to round-robin selection across official feeds and added per-feed
  health diagnostics.
- Tightened model/tool release filtering for guide/tutorial/case-study noise, added
  same-day near-duplicate release collapse, and exposed rejection diagnostics.
- Rebalanced Weekly Snapshot into a compact full-width featured-paper banner followed by
  equal-width repo, model-release, and tool/service cards. Repo previews now include a
  one-line description.
- Split GitHub `bestFor` labels so knowledge-management products and MCP tooling are not
  flattened into `RAG Infrastructure`; retrieval-specific terms now drive the RAG label.
- Refreshed README, top-level implementation plan, and architecture notes so they describe
  the six-tab dashboard, current artifact contract, source diagnostics, and next phases.
- Added GitHub Pages deployment through `.github/workflows/deploy-pages.yml`; the public
  dashboard URL is `https://ajinkyapawale1.github.io/ai-news-artifact/`.
- Renamed the npm package to `ai-news-artifact`; the intended GitHub repository slug is
  `ai-news-artifact`.
- Fixed mobile rendering by making the dashboard grids, header controls, tabs, research
  cards, release lists, and pipeline flow responsive with no horizontal overflow at 390px.
- Added OpenAI-backed action-item generation for displayed research papers with deterministic
  fallback, retry/disable diagnostics, artifact-compatible `papers[].actionItems`, focused
  unit coverage, and updated research-paper architecture docs.
- Added repo recommended actions with optional OpenAI generation and deterministic fallback,
  plus expanded repo-card action panels and rectangular release/open-repo CTAs.
- Removed RSS/source-feed CTAs from model/tool release cards; model cards now show a blue
  benchmark CTA and release/tool cards use yellow read-release CTAs.
- Tightened CTA sizing across dashboard links, moved expanded repo release/open-repo CTAs
  into the expanded header beside repo tags, and changed model benchmark fallbacks from
  the generic Artificial Analysis evaluations page to model-specific `/models/<slug>/`
  pages.
- Replaced guessed Artificial Analysis benchmark slugs with a verified allowlist plus
  safe models-directory fallback, moved hosted-model availability cards such as NEXUS
  on SageMaker into tools/services, and removed GPT-Rosalind capability updates from
  model releases.
- Removed runtime Tailwind CDN and Google Fonts dependencies; local utility CSS now
  covers the dashboard classes and production `npm run build` passes again.
- Fixed the recurring local dev hang where Vite listened on `5173` but did not respond:
  Vite now binds to `127.0.0.1`, uses esbuild JSX handling instead of the React Babel
  plugin, Lucide icons are imported directly to avoid barrel prebundling, and stale
  orphaned Vite/esbuild plus headless automation processes were cleaned up.
- Renamed the dashboard module to `ai-intelligence-brief.jsx` and removed the obsolete
  relevance flag from the generated contract.
- Added Monday-keyed repository archives under `data/archive/`, with idempotent same-week
  replacement and a newest-first manifest.
- Added a header edition selector that shows the current brief plus the three preceding
  archives and updates all tabs from the selected dataset.
- Extended the Pages workflow to refresh, validate, archive, commit, build, and deploy
  every Monday at 10:00 AM America/New_York.
- Added a tested publication gate that blocks commit and deployment on failed required
  sources, empty core lanes, or current/archive mismatch.
- Replaced eager archive imports with static `dist/archive/` assets and on-demand,
  session-cached fetching for the selected edition.

## Current State
- Project runs via Vite from `apps/web` using root npm scripts.
- Python pipeline fetches real arXiv, GitHub, and RSS items and writes `data/output.json`.
- GitHub repo bullets are generated deterministically by default and can use OpenAI when `OPENAI_API_KEY` is set.
- Dashboard reads generated JSON data. Current dev-server rendering was verified on
  `http://localhost:5173`; visible title load improved from roughly 11.8s to roughly
  0.57s after removing runtime CDN/font dependencies.
- Current dev server is running at `http://127.0.0.1:5173/`; normal cached startup
  measured about 130-184 ms, `/` returned in about 68 ms, and the main dashboard JSX
  module returned in about 32 ms after the Vite cache was ready.
- Dashboard renders properly on desktop and mobile; the mobile tab rail wraps and the
  pipeline flow stacks vertically.
- Dashboard branding and user-facing copy are generic rather than financial-services-specific.
- AI Pulse, Social Pulse, and Enterprise Focus intentionally render as coming-soon placeholders.
- Generated health log is written to `data/health.json`.
- Agent operating guidance is now centralized in `AGENTS.md`.
- Repo memory now includes context, decisions, handoff, tasks, and errors.
- The dashboard can now receive generated model release and AI tool/service cards with
  longer notes plus release links when current feed entries match deterministic and/or
  LLM classification; source-feed URLs are retained as metadata rather than visible CTAs.
- Model/tool dynamic state is persisted in `data/model_tools_dynamic_config.json`; health output includes extraction diagnostics and dynamic refresh metadata.
- `data/model_tools_dynamic_config.json` is generated inspectable state, not the primary contributor edit point; static defaults live in `apps/pipeline/src/news_pipeline/model_tools_config.py`.
- Latest refresh produced 3 model cards and 6 tool/service cards, all with resolved in-window dates and no `Unknown` values.
- The docs folder now includes separate architecture pages for research papers, GitHub discovery, and model/tool release discovery.
- Displayed research-paper cards now carry exactly three action items. OpenAI action
  generation runs when `OPENAI_API_KEY` is configured and falls back to deterministic
  review, experiment/evaluation, and risk/adoption actions.
- Displayed repo cards now carry exactly three action items. OpenAI repo briefs can provide
  them; deterministic clone, map-use-case, and review-release/issues/license actions are
  used when the API is unavailable or the artifact has not been refreshed.
- Model/tool cards no longer expose RSS/source feed buttons in the UI. Model cards use
  verified Artificial Analysis model URLs when known; otherwise they link to
  `https://artificialanalysis.ai/models` as `Benchmarks` to avoid 404s.
- Perplexity's official API changelog Markdown and the ElevenLabs blog are now
  permanent model/tool source pages. Live checks on 2026-06-08 extracted
  Perplexity Finance Search and Agent API updates plus ElevenLabs Dubbing v2,
  Music v2, Eleven v3, and ElevenLabs UI releases.
- No valid official RSS/Atom endpoint was found for either provider. Perplexity
  monthly changelog blocks use month-end dates only after the month completes;
  ElevenLabs blog posts retain their exact article publication dates.
- Source-page classification now requires a product signal in the headline and rejects
  corporate expansion/partnership announcements that mention products only in body text.
- Review regression coverage confirms current-month changelog blocks remain excluded on
  the final day; all 56 pipeline tests, Ruff, and touched-file compilation pass.
- `origin` should point to `https://github.com/AjinkyaPawale1/ai-news-artifact.git`
  after the repository rename.
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
11. Design the broader enterprise credibility, actionability, and personalization scoring phase before implementing it.

## Risks / Watchouts
- If utility classes expand, local utility CSS may become less maintainable than a real
  local Tailwind pipeline; do not reintroduce runtime Tailwind CDN for the dashboard.
- GitHub API runs unauthenticated unless GITHUB_TOKEN is provided; rate limits may apply.
- LangGraph is now a pipeline dependency; run `pip install -r apps/pipeline/requirements.txt` after pulling.
- OpenAI repo summaries are optional and require `OPENAI_API_KEY`; `OPENAI_MODEL` defaults to `gpt-5.4-mini`.
- OpenAI repo recommended actions share `OPENAI_REPO_BRIEF_LIMIT`; missing or invalid
  `actionItems` fall back deterministically while keeping repo bullets available.
- OpenAI paper summaries and paper action items are optional and require `OPENAI_API_KEY`;
  both paths disable later calls for their own path after auth/quota failures and publish
  diagnostics under the papers health entry.
- Some RSS feeds may fail or return sparse content; health log captures source-level status.
- Model/tool extraction remains deterministic-first, but official source pages can pass release-signal checks and may rely on LLM classification for final card naming and notes.
- The model/tool workflow now drops entries when a recent publish date cannot be resolved; this avoids `Unknown` cards and stale releases, but it can reduce weekly card count when provider pages omit publish metadata.
- Optional model/tool LLM behavior is bounded: it proposes emerging feed/keyword rotations from a candidate catalog and classifies only limited candidate entries.
- `429 insufficient_quota` from OpenAI is an API billing/quota issue, not a normal transient rate limit; see `memory/errors.md` before retry loops.
- Root `data/output.json` is a shared interface; keep pipeline-owned writes and frontend reads separate.
- Full pipeline runs also update `data/archive/index.json`; paper-only refreshes intentionally
  update only the current artifact and do not create a weekly archive.
- A failed scheduled publication gate leaves generated changes uncommitted on the
  disposable runner, so the existing public Pages edition remains live.
- Paper research metadata and scores are deterministic keyword logic; adjust keyword groups and score weights carefully if dashboard labels or ranking feel too broad or too narrow.
- arXiv runs intentionally add three-second spacing between category requests to reduce avoidable `429` responses.
- If installed binaries hang on macOS, clear quarantine metadata from `node_modules` with `xattr -dr com.apple.quarantine node_modules`.
- On 2026-06-04, `npm run build` initially timed out at Vite `transforming...`; after
  removing runtime Tailwind CDN and Google Fonts imports, the build completed in 1.87s.
- Keep `AGENTS.md` and the `memory/` files in sync when agent operating rules change.
- This checkout is a git worktree; GitHub CLI repository creation works more reliably by creating the remote first, then adding `origin`, rather than using `gh repo create --source=.`.

## Quick Resume Steps
- npm install
- pip install -r apps/pipeline/requirements.txt
- npm run pipeline
- npm run dev
- Open local URL shown by Vite
- Read `AGENTS.md` plus relevant files under `memory/` before new implementation work.
