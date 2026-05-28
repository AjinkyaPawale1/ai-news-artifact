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
npm run dev
npm run build
npm run preview
```
