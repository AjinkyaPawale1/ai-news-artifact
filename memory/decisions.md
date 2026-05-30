# Decision Log

## 2026-05-04 - Use Vite React wrapper for standalone JSX component
Status: accepted

Reason:
- The source file is a React component, not directly executable as a script.
- Vite provides the fastest local dev runtime for JSX with minimal config.

Impact:
- Added package.json, vite.config.js, index.html, and src entry files.
- Project now runs with npm scripts.

## 2026-05-04 - Keep repo-level agent memory under version control
Status: accepted

Reason:
- Future human/AI contributors need deterministic handoff context.
- Versioned memory avoids context loss between sessions.

Impact:
- Added agent.md and memory/* files with update protocol.

## 2026-05-11 - Build agent pipeline in Python and keep frontend in React
Status: accepted

Reason:
- Python is better suited for feed parsing, data processing, scoring, and future LLM/NLP work.
- The existing Vite React dashboard already works well as the frontend.

Impact:
- Added Python pipeline under pipeline/ with supervisor, fetch agents, schema/config, scoring stubs, quality gate, artifact writer, and health logging.
- Added data/output.json as the frontend data artifact.
- Added npm run pipeline as a wrapper for python3 pipeline/supervisor.py.

## 2026-05-14 - Adopt Monorepo Lite structure
Status: accepted

Reason:
- The project has two clear runtimes: React/Vite frontend and Python agentic pipeline.
- A lightweight monorepo boundary keeps those runtimes separate without adding heavy workspace tooling.
- Root `data/output.json` remains the explicit artifact contract between backend and frontend.

Impact:
- Moved the frontend into `apps/web`.
- Moved the Python pipeline into the `news_pipeline` package under `apps/pipeline/src`.
- Kept root npm scripts as the main developer entry points.
- Added `docs/architecture.md` for the current data flow and repository layout.

## 2026-05-14 - Use Rollup WASM package alias for Vite builds
Status: accepted

Reason:
- The local macOS dependency install had native binary launch issues during Vite build validation.
- The WASM-backed Rollup package provides the same Rollup interface without relying on the native Rollup addon.

Impact:
- Added a direct dev dependency alias: `rollup` -> `@rollup/wasm-node`.
- Vite build validation completes successfully from the root npm script.

## 2026-05-15 - Use LangGraph for GitHub repo discovery
Status: accepted

Reason:
- GitHub discovery needs a multi-step agent flow: search, enrich, score, summarize, and emit dashboard items.
- LangGraph keeps that flow explicit and aligns with the project direction for agent structure.
- The pipeline should still run without an OpenAI key.

Impact:
- Added `news_pipeline.agents.github_graph` with a LangGraph StateGraph for repo discovery.
- GitHub items now carry repo metadata, bullets, traction score, latest release, and related links.
- OpenAI-generated repo briefs are optional via `OPENAI_API_KEY`; deterministic bullets remain the fallback.
- The dashboard repo section now expands to show repo details and links out to GitHub.

## 2026-05-20 - Rename agent guide to AGENTS.md and expand operating rules
Status: accepted

Reason:
- `AGENTS.md` is a common repository instruction filename for coding agents.
- The original guide captured repo memory basics but did not fully encode coding-agent behavior, approval rules, repeated-error tracking, or session-end memory updates.
- The updated guide incorporates Karpathy-style coding principles and the X-thread recommendations around memory, scope control, confirmations, and technical-stack locking.

Impact:
- Renamed `agent.md` to `AGENTS.md`.
- Added stricter guidance for thinking before coding, simplicity, surgical changes, and verification.
- Added approval rules for major, destructive, deployment, publishing, and other side-effectful actions.
- Added `memory/errors.md` for repeated failures and troubleshooting lessons.
- Updated repo memory files to reference the expanded protocol.

## 2026-05-28 - Extract model releases and tools/services as classified RSS items
Status: accepted

Reason:
- The dashboard already had compact `models` and `toolsServices` card contracts.
- RSS-style vendor feeds are the lowest-friction source for launch and service announcements.
- A deterministic classifier keeps user-facing copy clean and avoids model-dependent labels for weekly runs.

Impact:
- Added `news_pipeline.agents.model_tools_graph` with a LangGraph workflow and sequential fallback.
- Added `model` and `tool_service` source types and artifact mapping for generated release cards.
- Exact-URL dedupe now preserves specific model/tool classifications over duplicate generic RSS entries.

## 2026-05-28 - Use bounded LLM assistance for model/tool discovery freshness
Status: accepted

Reason:
- Static feeds and keywords are too brittle for fast-moving model/tool launches.
- A fully LLM-owned feed and relevance system would be harder to debug and could drift.
- The GitHub dynamic workflow already provides a bounded proposal pattern.

Impact:
- Added protected core model/tool feeds plus a rotating emerging feed and keyword layer.
- OpenAI can propose emerging feed/keyword updates from a candidate catalog when configured.
- OpenAI can classify a limited number of candidate model/tool entries, while deterministic classification remains the fallback.

## 2026-05-28 - Use official source pages when provider RSS is unavailable
Status: accepted

Reason:
- Several important providers do not expose reliable parseable RSS for model and tool launches.
- Official source pages are still more trustworthy than broad web search for release-card candidates.
- Source-page links can be noisy, so deterministic URL/title filtering and bounded LLM classification are still required.

Impact:
- Added source-page extraction for Anthropic, Gemini API changelog, Meta AI, Mistral, and Cohere.
- Source-page candidates are enriched with article excerpts when possible before final classification.
- Model/tool cards now expose both the release URL and the originating source feed/page URL.

## 2026-05-28 - Require recent resolved dates for model/tool release cards
Status: accepted

Reason:
- Weekly model/tool filtering breaks when cards keep `Unknown` dates or inherit stale source-page links.
- Vendor feeds and source pages vary widely, so date resolution needs multiple fallbacks before an item is trusted.
- If a recent publish date still cannot be resolved, dropping the card is safer than showing a misleading weekly release.

Impact:
- Model/tool extraction now resolves publish dates from feed timestamps, HTML metadata, date-like URL paths, visible article text, and fallback response headers.
- Entries without a resolved in-window date are excluded from `models` and `toolsServices`.
- The dashboard model/tool sections now behave like the repo list: collapsed rows by default with clickable expansion for the full summary and links.

## 2026-05-29 - Publish this worktree to a new private GitHub repository
Status: accepted

Reason:
- The current local project needed a live private remote under the user's GitHub account.
- This checkout is a git worktree, so `gh repo create --source=.` was not a reliable creation path.
- The first pushed branch became the GitHub default branch automatically, which needed normalization back to `main`.

Impact:
- Created the private repository `AjinkyaPawale1/llm-news-artifact`.
- Added `origin` pointing at the new repository and pushed `main`, `feature/model-tools-releases-workflow`, and `feature/paper-actions-workflow`.
- Set the repository default branch to `main` after the initial push.

## 2026-05-30 - Centralize model/tools agent configuration
Status: accepted

Reason:
- Model/tools feeds, terms, and limits had become distributed across pipeline config, graph code, generated state, and artifact mapping.
- Contributors need one human-maintained configuration home and one documented vocabulary for source ownership.

Impact:
- Added `news_pipeline.model_tools_config` for static source groups, core terms, toggles, and numeric limits.
- Kept generated emerging state in `data/model_tools_dynamic_config.json` for inspection and continuity.
- Standardized core, emerging, and candidate terminology.
- Made `MODEL_TOOL_MAX_ITEMS` the shared per-category cap for graph selection and dashboard rendering.
