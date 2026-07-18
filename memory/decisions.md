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

## 2026-05-28 - Use deterministic paper action metadata
Status: accepted

Reason:
- arXiv papers need dashboard-ready takeaways and action items without depending on an LLM call.
- The repo already prefers deterministic labels where UI output should remain stable.
- Paper enrichment is a small workflow step and should align with the LangGraph/LangChain pattern used for agent flows.

Impact:
- Added `news_pipeline.agents.paper_graph` to enrich paper `Item.metadata`.
- `fetch_papers` now returns papers with priority, takeaways, action items, relevance, verticals, and code signals.
- `push_to_artifact` maps those fields into dashboard paper cards and top action items.

## 2026-06-01 - Use generic paper discovery and independent research ranking
Status: accepted

Reason:
- Paper discovery should cover broad AI/ML research instead of applying financial-services domain assumptions during enrichment and ranking.
- Research-card ranking and the mixed-source action queue answer different questions and need separate explainable scores.
- A single arXiv category rate limit should not discard useful results from other categories.

Impact:
- Paper metadata now uses generic capability and domain taxonomies, generic research tags, visible research signals, and a deterministic `research_score`.
- The dashboard emits the top eight available papers by research score and replaces the financial-services relevance grid with generic research signals.
- The mixed-source action queue uses a separate generic `action_score`.
- Paper fetches retain partial arXiv results and publish per-category diagnostics.

## 2026-06-01 - Add bounded paper backfill and optional OpenAI summaries
Status: accepted

Reason:
- Weekly paper cards should prioritize freshness without leaving the dashboard sparse.
- Paper takeaways should summarize the abstract rather than repeat generic workflow advice.
- The dashboard needs concise paper cards with minimal tags and an obvious source link.

Impact:
- Paper selection uses seven days first and fills missing top-eight slots from days 8-14 only.
- Displayed papers receive exactly three abstract-grounded bullets, optionally generated through the OpenAI Responses API with deterministic fallback.
- Paper cards show two tags and a highlighted yellow `OPEN PAPER` link.

## 2026-06-01 - Keep the weekly briefing research-paper focused
Status: accepted

Reason:
- Research papers, trending repositories, model releases, and tools/services should remain separate dashboard sections instead of competing in one mixed action queue.

Impact:
- The weekly briefing left section is labeled `RESEARCH PAPERS` and shows ranked paper cards.
- The previous consultant-curation subtitle and mixed-source action-card UI were removed.
- The retained `actionItems` artifact compatibility field now contains papers only.

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

## 2026-06-02 - Make paper curation resilient and expose recommended actions
Status: accepted

Reason:
- arXiv category calls occasionally return transient failures and should not rely on a single request.
- OpenAI paper summaries are the preferred card copy when a key exists, but deterministic bullets must preserve weekly output when the API is unavailable.
- Raw substring labels caused weak domain matches such as `learning` forcing an education label.
- Paper priorities and recommended actions existed in the artifact but were not visible in the paper card.

Impact:
- Paper fetching now uses explicit LangGraph fetch, recent-selection, and metadata-enrichment stages with sequential fallback.
- arXiv requests are paced and retry transient failures twice with exponential backoff and jitter.
- Paper summaries retry transient OpenAI failures twice and publish summary diagnostics with deterministic fallback behavior.
- Capability and domain labels use weighted phrase matching with weak or tied domains falling back to `Other`.
- Paper cards render a priority chip and expanded recommended actions while `research_score` remains the ranking signal.

## 2026-06-02 - Use a neutral decision-first dashboard and targeted pipeline cleanup
Status: accepted

Reason:
- The previous weekly page repeated the Research tab and overloaded the landing view with full lists.
- Financial-services branding and domain-injection copy no longer matched the generic AI intelligence goal.
- RSS ordering and permissive release classification created avoidable source imbalance and noisy cards.

Impact:
- The dashboard now uses Weekly Snapshot, Research, Repos, Releases, Signals, and Pipeline tabs.
- AI Pulse, Social Pulse, and Enterprise Focus are explicit placeholders.
- Snapshot stats describe selected artifact content and latest source health rather than a misleading relevance count.
- RSS selection is round-robin across official feeds.
- Model/tool filtering rejects non-release article patterns and collapses same-day near-duplicate product names while preserving distinct versions.
- Broader enterprise credibility and actionability scoring is deferred to a dedicated later phase.

## 2026-06-02 - Rebalance the snapshot and narrow GitHub repo labels
Status: accepted

Reason:
- The featured paper stretched beside three stacked cards and left a large empty area.
- GitHub repo labels treated broad knowledge and context terms as RAG signals, which made
  unrelated snapshot cards appear to share the same domain.

Impact:
- Weekly Snapshot uses a full-width paper banner followed by three equal-width preview
  cards for repos, model releases, and tools/services.
- Repo previews include one-line descriptions from the generated artifact.
- GitHub labels separate `Knowledge Management`, `MCP Tooling`, and retrieval-specific
  `RAG Infrastructure`; bare `context` mentions no longer imply RAG.

## 2026-06-02 - Publish the static dashboard through GitHub Pages
Status: accepted

Reason:
- The dashboard needs a shareable public URL for email and internet sharing.
- A static artifact deployment fits the current architecture because the frontend reads
  generated JSON bundled at build time and does not require an API service.

Impact:
- The repository slug is `ai-news-artifact` and the npm package name matches it.
- GitHub Pages publishes the dashboard at `https://ajinkyapawale1.github.io/ai-news-artifact/`.
- The Pages workflow builds from `main`, uploads root `dist`, and sets `GITHUB_PAGES=true`
  so Vite uses the `/ai-news-artifact/` base path.

## 2026-06-03 - Generate displayed paper action items with bounded OpenAI fallback
Status: accepted

Reason:
- Research cards need specific action items, not only deterministic generic prompts.
- The dashboard contract still requires `papers[].actionItems` to remain a list of strings.
- The paper workflow must remain usable without an API key, quota, or valid LLM response.

Impact:
- Displayed papers now attempt OpenAI Responses API action generation after paper summaries.
- Each paper action list is normalized to exactly three non-repetitive strings: immediate
  review action, experiment/evaluation action, and risk/adoption question.
- Missing keys, auth/quota failures, transient failures, invalid JSON, and invalid action
  shapes fall back to deterministic actions and emit action diagnostics in paper health.

## 2026-06-03 - Add repo action items and simplify release CTAs
Status: accepted

Reason:
- Repo cards should provide the same next-step clarity as research cards.
- Repo actions should benefit from LLM context when available but remain deterministic
  when no API key, quota, or valid response exists.
- Model/tool cards should link to useful release and benchmark destinations, not RSS
  feeds or source-page indexes.

Impact:
- GitHub repo metadata now includes exactly three `action_items`, generated by OpenAI
  repo briefs when available and otherwise produced by deterministic clone, workflow
  mapping, and release/issues/license review prompts.
- The dashboard maps those actions into `repos[].actionItems` and shows an expanded
  `RECOMMENDED ACTIONS` panel; current artifacts without that field get a frontend
  deterministic fallback.
- Model/tool release cards no longer render RSS/source-feed CTAs. Model cards show
  yellow `Read release` plus blue `Benchmark`; tool/service cards show only yellow
  `Read release`.

## 2026-06-04 - Tighten release CTAs and repo expanded-card layout
Status: accepted

Reason:
- Generic Artificial Analysis evaluation links made model benchmark CTAs less useful
  than a model-specific destination.
- Expanded repo cards left release/open-repo CTAs visually detached from the repo
  metadata and created too much empty space.
- Release CTAs were visually heavier than the notes they support.

Impact:
- Model benchmark links now fall back to Artificial Analysis model-page slugs derived
  from the release name, with existing explicit benchmark URLs still respected.
- Repo expanded cards place release/open-repo CTAs in the expanded header next to
  repo tags, followed by a balanced takeaways/actions grid.
- Shared CTA sizing is more compact across research, repo, model-release, and
  tool/service links.

## 2026-06-04 - Verify benchmark links and remove runtime CSS CDNs
Status: accepted

Reason:
- Guessing Artificial Analysis model slugs created 404-prone benchmark links.
- Hosted-model availability posts were polluting the strict model-release lane.
- The dev dashboard was slow/blank on first load because it depended on runtime
  Tailwind and Google Fonts network requests.

Impact:
- Model benchmark links now use a maintained verified Artificial Analysis allowlist;
  unverified models link to the Artificial Analysis models directory as `Benchmarks`.
- Hosted distribution announcements such as SageMaker JumpStart, Bedrock, Foundry,
  AWS/Azure availability, and NVIDIA deployment posts classify as tools/services.
- Model capability-update headlines without a new model, such as `new capabilities to`,
  are rejected from model releases.
- The frontend no longer loads Tailwind CDN or Google Fonts at runtime; needed layout
  utilities are local CSS, and production build verification passes again.

## 2026-06-08 - Archive weekly editions and publish Monday mornings
Status: accepted

Reason:
- Readers need access to recent briefs without introducing a database or separate service.
- The existing static artifact and GitHub Pages architecture can support versioned editions.
- Publication must remain at 10:00 AM Eastern across daylight-saving changes.

Impact:
- Full pipeline runs write an idempotent Monday-keyed output and health snapshot under
  `data/archive/` and update a newest-first manifest.
- The dashboard offers the current edition plus the three preceding archives from its header.
- GitHub Actions runs both possible UTC offsets and uses an America/New_York gate before
  refreshing, validating, committing generated artifacts, and deploying Pages.

## 2026-06-08 - Fail closed on incomplete refreshes and fetch archives on demand
Status: accepted

Reason:
- Source agents can preserve pipeline execution while reporting a failed top-level lane,
  which must not become a public weekly edition.
- Eagerly importing every archive makes the initial JavaScript payload grow every week.

Impact:
- A tested publication gate blocks commits and deployment when required source health,
  minimum content, or current/archive consistency checks fail.
- Partial internal paper-category recovery remains publishable when the top-level paper
  source succeeds.
- Historical outputs are static Pages assets fetched only when selected and cached for
  the browser session; archive count no longer increases the initial JavaScript bundle.

## 2026-06-08 - Add Perplexity and ElevenLabs as permanent official source pages
Status: accepted

Reason:
- Guessed official RSS/Atom endpoints either returned Cloudflare blocks, HTML, or 404s.
- Perplexity publishes a machine-readable official API changelog, and ElevenLabs
  publishes release posts with exact article dates on its official blog.
- Unofficial RSS mirrors would weaken source provenance and reliability.

Impact:
- Added both providers to the protected permanent source-page list rather than
  the rotating emerging-feed list.
- Perplexity completed monthly changelog blocks produce dated release candidates
  using month-end, avoiding invented intra-month publication dates.
- Release-style source-page headlines can use verified article body signals for
  deterministic classification, while integration, endpoint, and Agent API
  announcements remain in the tool/service lane.

## 2026-06-08 - Require completed months and product-focused source headlines
Status: accepted

Reason:
- A month-end timestamp becomes earlier than the current time during the final day,
  even though the provider can still add entries before the month closes.
- Generic release words plus model/tool mentions in article body text admitted corporate
  expansion and partnership announcements that did not ship a product.

Impact:
- Monthly changelog blocks remain ineligible throughout their labeled calendar month and
  become eligible on the first day of the following month.
- Source-page candidates require a product-focused headline; corporate expansion and
  partnership headlines are rejected even when their body mentions models or platforms.

## 2026-07-17 - Fail closed on public RSS quality
Status: accepted

Reason:
- The weekly artifact included title-only, tutorial, customer-story, and weakly relevant
  RSS entries, which weakens a public enterprise brief even when their source is official.
- A readable source URL and a complete, decision-useful takeaway are minimum publication
  requirements rather than presentation enhancements.

Impact:
- RSS candidates must pass deterministic editorial relevance checks, canonical metadata
  recovery when needed, and link verification before they can pass scoring or selection.
- Publication is blocked when a current RSS card lacks a verified URL or a complete
  summary. This introduces the additive `blogs[].linkVerified` field without changing
  the dashboard's existing card shape.

## 2026-07-17 - Reuse validated sections when a weekly lane is empty
Status: accepted

Reason:
- An empty dashboard section makes a temporary upstream gap appear as missing product
  capability, even when the previous edition contains valid, recent material.

Impact:
- The artifact writer preserves non-empty current sections and falls back only for an
  entirely empty section. It selects the newest structurally valid prior section within
  four weeks, stores additive `fallbackSections` provenance, and keeps original dates.
- The dashboard labels reused sections as a previous verified edition. Partially filled
  current sections are never padded with older cards.
- Publication now requires both model and tool/service sections independently, so a
  missing fallback blocks the new edition instead of publishing an empty release column.
