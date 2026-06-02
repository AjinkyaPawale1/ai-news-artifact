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
  -> React dashboard reads generated artifact
```

## Frontend

- Location: `apps/web`
- Runtime: Vite + React
- Entry point: `apps/web/src/main.jsx`
- Dashboard component: `apps/web/src/ey-fso-ai-brief.jsx`
- Shared artifact import: `data/output.json`

The frontend treats `data/output.json` as a read-only contract and does not call pipeline internals directly.

## Pipeline

- Location: `apps/pipeline`
- Package: `news_pipeline`
- Entry point: `news_pipeline.supervisor`
- Fetch agents:
  - `news_pipeline.agents.fetch_papers`
  - `news_pipeline.agents.fetch_github`
  - `news_pipeline.agents.fetch_rss`

The pipeline owns `data/output.json` and `data/health.json`. No API service is part of the current architecture.

## Paper Discovery Methodology

The paper source queries the latest `cs.AI`, `cs.CL`, and `cs.LG` arXiv entries and
starts with papers from the seven-day brief window. If fewer than eight unique papers
are available, it backfills only the remaining slots from days 8-14. One failed
category does not discard successful category results.

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

The artifact emits the top eight available papers. The weekly briefing also uses ranked
papers only; repos, releases, and tools/services remain separate dashboard sections.
Paper health diagnostics include per-category status plus raw, seven-day, fourteen-day,
backfill, deduplicated, and displayed counts.

The eight displayed papers receive exactly three abstract-grounded summary bullets.
When `OPENAI_API_KEY` is configured, the Responses API produces those bullets with
`OPENAI_MODEL` and an `OPENAI_PAPER_SUMMARY_LIMIT` cap. Without a key or after an API
failure, the pipeline falls back to deterministic abstract sentences.

Use `npm run pipeline:papers` to refresh papers, paper-derived compatibility action items,
and paper health diagnostics without fetching or replacing the existing repos, blogs,
models, or tools/services.

## GitHub Discovery Methodology

The GitHub source uses a dedicated LangGraph workflow documented in `docs/github-agent-architecture.md`.

Current behavior in the codebase:

- Two query tiers: core + emerging (`GITHUB_ENABLE_EMERGING_QUERIES` controls inclusion).
- Dynamic runtime resolver refreshes emerging queries/watch repos each run (`resolve_dynamic_github_inputs`) and persists state in `data/github_dynamic_config.json`.
- Anthropic repositories are part of evergreen defaults (for example, `anthropics/anthropic-sdk-python`, `anthropics/anthropic-cookbook`).
- Query-level diagnostics are captured (`fetched`, `added`, `failed`) and written under the GitHub entry in `data/health.json`.
- Dynamic refresh diagnostics are also written to `data/health.json` (`dynamic_config`, `dynamic_refresh`).
- Relevance uses a tiered keyword taxonomy (core, emerging, framework) plus an emerging-topic bonus.
- Selection uses tiered thresholds:
  - `TRACTION_THRESHOLD_DEFAULT` for standard repos.
  - `TRACTION_THRESHOLD_EMERGING` for repos with emerging-topic hits.
- Guardrails bound auto-updater churn via `GITHUB_DYNAMIC_MAX_QUERY_REPLACEMENTS` and `GITHUB_DYNAMIC_MAX_WATCH_REPLACEMENTS`.
- Artifact stats intentionally separate pool size from display size (`REPOS INDEXED` with `8 shown`).

For full flowcharts and draw.io-style diagrams, see:

- `docs/github-agent-architecture.md`
- `docs/assets/github-agent-flow.svg`

## Commands

Run from the repository root:

```sh
npm run pipeline
npm run pipeline:papers
npm run dev
npm run build
npm run preview
```
