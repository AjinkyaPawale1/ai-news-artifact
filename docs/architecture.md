# Architecture

This repository uses a lightweight monorepo layout for a React dashboard and a Python agentic artifact pipeline.

## Repository Layout

```text
apps/
  web/                 React + Vite dashboard
  pipeline/            Python news pipeline package
data/                  Shared generated artifacts
memory/                Versioned project context and handoff notes
docs/                  Architecture and contributor documentation
```

## Data Flow

The Python pipeline is the backend boundary. It runs on demand or on a schedule, fetches and processes news items, and writes JSON artifacts into the root `data/` directory.

```text
fetch agents
  -> deduplicate
  -> normalize
  -> score
  -> quality gate
  -> summarize
  -> write data/output.json and data/health.json
  -> archive the Monday edition under data/archive/
  -> React dashboard reads generated artifact
```

The shared deduplicator canonicalizes HTTP(S) URLs, removes tracking-only variants,
normalizes arXiv and GitHub URL forms, and applies conservative fuzzy-title matching only
within compatible paper, repository, or release families. When duplicate records point to
different source URLs, the selected representative retains the others in `related_links`.
Normalization then validates required fields and HTTP(S) URLs, standardizes dates and
list fields, and drops records that cannot satisfy the shared `Item` contract.

## Frontend

- Location: `apps/web`
- Runtime: Vite + React
- Entry point: `apps/web/src/main.jsx`
- Dashboard component: `apps/web/src/ai-intelligence-brief.jsx`
- Shared artifact imports: `data/output.json` and `data/archive/index.json`

The frontend treats generated JSON as a read-only contract and does not call pipeline internals directly.
It defaults to the current artifact and exposes the three preceding weekly editions through
the header selector when those archives exist. Historical output files are copied to
`dist/archive/` as static assets and fetched only when selected; they are not included in
the initial JavaScript bundle.
Its neutral `AI Intelligence Brief` shell uses six views:

- `Weekly Snapshot` for a decision-first overview with one full-width featured-paper banner
  followed by equal-width repo, model-release, and tool/service previews.
- `Research`, `Repos`, and `Releases` for full drill-down lists.
- `Signals` for explicit AI Pulse and Social Pulse placeholders.
- `Pipeline` for the current artifact flow and live health diagnostics.

The published static dashboard is served through GitHub Pages at:

- `https://ajinkyapawale1.github.io/ai-news-artifact/`

Local Vite builds use `/` as the base path. The Pages workflow sets
`GITHUB_PAGES=true`, which makes Vite build with `/ai-news-artifact/`.

## Pipeline

- Location: `apps/pipeline`
- Package: `news_pipeline`
- Entry point: `news_pipeline.supervisor`
- Fetch agents:
  - `news_pipeline.agents.fetch_papers`
  - `news_pipeline.agents.fetch_github`
  - `news_pipeline.agents.fetch_rss`
  - `news_pipeline.agents.model_tools_graph`

The pipeline owns `data/output.json`, `data/health.json`, and `data/archive/`. A successful
full run writes an idempotent Monday-keyed snapshot and updates `data/archive/index.json`.
No API service is part of the current architecture.

## Weekly Automation and Archives

GitHub Actions runs the full pipeline every Monday at 10:00 AM America/New_York, commits
the generated current and archive artifacts, builds the dashboard, and deploys GitHub
Pages. Two UTC schedules cover daylight-saving changes; a timezone gate allows only the
10:00 AM Eastern run to proceed.

Before commit or deployment, `news_pipeline.publication_gate` requires one healthy
top-level result for papers, GitHub, RSS, and model/tools, plus non-empty paper, repo,
blog, model, and tool/service sections. Internal partial paper-category recovery remains
allowed when the top-level paper workflow succeeds. A failed gate leaves the previously
published Pages edition unchanged.

Before writing a weekly artifact, the pipeline preserves current valid content and fills
only an entirely empty dashboard section from the newest structurally valid, source-healthy
prior edition within four weeks. Reused data is recorded in additive
`fallbackSections` provenance, retains its original card dates, and is labeled in the
dashboard as a previous verified edition. Partially populated sections are never padded
with historical cards.

Each weekly edition contains:

- `data/archive/YYYY-MM-DD/output.json`
- `data/archive/YYYY-MM-DD/health.json`
- one corresponding entry in `data/archive/index.json`

Rerunning the pipeline during the same publication week replaces that Monday's snapshot.
Older editions remain versioned in Git, while the UI limits its selector to the three
immediately preceding editions. Selected archives are cached in memory for the browser
session; failed requests fall back to the current edition.

## Paper Discovery Methodology

The paper source queries the latest `cs.AI`, `cs.CL`, and `cs.LG` arXiv entries and
starts with papers from the seven-day brief window. If fewer than eight unique papers
are available, it backfills only the remaining slots from days 8-14. One failed
category does not discard successful category results. arXiv requests are paced by
three seconds and retry transient failures twice with exponential backoff and jitter.

Paper enrichment produces a primary capability, a descriptive domain, action priority,
takeaways, action items, tags, code-availability signal, research score, and visible
research-signal levels. Domain labels are descriptive only and do not filter or score
papers.

Paper cards are ranked independently from other sources with an explainable `0-100`
research score:

| Component | Weight |
| --- | ---: |
| AI/ML topical fit | 25 |
| Evidence and evaluation | 20 |
| Practical applicability | 20 |
| Reproducibility | 15 |
| Novelty or emerging signal | 10 |
| Recency within the seven-day window | 10 |

The artifact emits the top eight available papers. The weekly snapshot features the
top paper only; the full ranked list lives under `Research`.
Paper health diagnostics include per-category status, retry attempts, plus raw,
seven-day, fourteen-day, backfill, deduplicated, displayed, and summary counts.

The eight displayed papers receive exactly three abstract-grounded summary bullets.
When `OPENAI_API_KEY` is configured, the Responses API produces those bullets by default
with `OPENAI_MODEL`, an `OPENAI_PAPER_SUMMARY_LIMIT` cap, and two transient retries.
Without a key or after exhausted retries, the pipeline falls back to deterministic
abstract sentences.

Use `npm run pipeline:papers` to refresh papers, paper-derived compatibility action items,
and paper health diagnostics without fetching or replacing the existing repos, blogs,
models, or tools/services.

For the full research-paper flow, including the LangGraph state, arXiv extraction,
research scoring, default OpenAI summary bullets, paper-only refresh path, diagnostics,
and artifact mapping, see:

- `docs/research-paper-agent-architecture.md`

## GitHub Discovery Methodology

The GitHub source uses a dedicated LangGraph workflow documented in `docs/github-agent-architecture.md`.

Current behavior in the codebase:

- Two query tiers: core + emerging (`GITHUB_ENABLE_EMERGING_QUERIES` controls inclusion).
- Dynamic runtime resolver refreshes emerging queries/watch repos each run (`resolve_dynamic_github_inputs`) and persists state in `data/github_dynamic_config.json`.
- Anthropic repositories are part of evergreen defaults (for example, `anthropics/anthropic-sdk-python`, `anthropics/anthropic-cookbook`).
- Query-level diagnostics are captured (`fetched`, `added`, `failed`) and written under the GitHub entry in `data/health.json`.
- Dynamic refresh diagnostics are also written to `data/health.json` (`dynamic_config`, `dynamic_refresh`).
- Relevance uses a tiered keyword taxonomy (core, emerging, framework) plus an emerging-topic bonus.
- Repo `bestFor` labels are deterministic and distinguish knowledge-management products,
  MCP tooling, retrieval-specific RAG infrastructure, coding workflows, model serving,
  AI agent apps, data extraction, security, research, and memory/reasoning systems.
- Displayed repo cards carry exactly three recommended actions. OpenAI can generate
  those actions with the repo brief when `OPENAI_API_KEY` is available; deterministic
  clone, map-a-use-case, and review-release/issues/license actions remain the fallback.
- Selection uses tiered thresholds:
  - `TRACTION_THRESHOLD_DEFAULT` for standard repos.
  - `TRACTION_THRESHOLD_EMERGING` for repos with emerging-topic hits.
- Guardrails bound auto-updater churn via `GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS` and `GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS`.
- Artifact stats intentionally separate pool size from display size (`REPOS INDEXED` with `8 shown`).
- Expanded repo cards show the recommended actions plus rectangular `RELEASE` and
  `OPEN REPO` CTAs.

For full flowcharts and draw.io-style diagrams, see:

- `docs/github-agent-architecture.md`
- `docs/assets/github-agent-flow.svg`

## RSS Collection Methodology

The RSS collector reads configured official feeds independently, filters each feed to
the active date window, rejects tutorial, customer-story, and weakly decision-relevant
items, then selects entries round-robin within the shared RSS cap. Sparse feed excerpts
are enriched from canonical page metadata and visible URLs are verified before an item
can enter the public artifact. This prevents an early high-volume feed from consuming
the complete visible article budget while keeping the visible RSS lane decision-useful.
The latest run stores per-feed fetched, eligible, verified, rejected, and selected counts
under the RSS entry in `data/health.json`.

Model/tool release cards do not render RSS or source-page feed links. Model cards show
a yellow `Read release` CTA plus a blue benchmark CTA only after mapping to a verified
Artificial Analysis model page; unverified models link to the Artificial Analysis models
directory as `Model directory` instead of inventing a model URL. Tool/service cards show only
the yellow `Read release` CTA. Source URLs remain in the artifact metadata for audit
and diagnostics.

## Dashboard Statistics

The snapshot stats describe the artifact contract directly:

- `PAPERS REVIEWED` with the selected paper count.
- `REPOS INDEXED` with the visible repo count.
- `RELEASES TRACKED` split into models and tools.
- `HEALTHY SOURCES` from the latest `data/health.json` statuses.

Broader enterprise credibility and actionability scoring remains a later pipeline phase.

## Enterprise Relevance Positioning

The brief is designed for enterprise AI experimentation and adoption decisions, but it is
not a personalized enterprise recommender. The current controls establish a reliable
baseline:

- RSS cards must be AI-relevant, decision-relevant, summary-complete, and link-verified;
  tutorials, customer stories, and onboarding content are excluded.
- Model and tool/service cards require concrete release or availability signals in their
  headlines. Consumer-rollout and education announcements are excluded unless they
  describe a concrete enterprise product change.
- Papers are ranked by generic research signals, and repositories by engineering traction
  and diversity. Neither lane currently applies organization-specific business context,
  risk posture, or adoption priorities.

Broader enterprise credibility, actionability, and personalization scoring remains an
explicit next phase rather than an implied property of every card.

## Commands

Run from the repository root:

```sh
npm run pipeline
npm run pipeline:papers
npm run dev
npm run build
npm run preview
```

## GitHub Pages Deployment

- Workflow: `.github/workflows/deploy-pages.yml`
- Trigger: pushes to `main` and manual `workflow_dispatch`
- Build command: `npm run build`
- Published artifact: root `dist`
- Vite Pages base: `/ai-news-artifact/`
