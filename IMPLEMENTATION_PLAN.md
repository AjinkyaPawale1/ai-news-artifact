# LLM News Artifact - Implementation Plan

**Updated:** 2026-05-14  
**Repository shape:** Monorepo Lite  
**Goal:** Maintain a React intelligence brief dashboard backed by a Python agentic pipeline that fetches, filters, scores, and publishes AI/LLM news into a shared JSON artifact.

---

## Current Architecture

The project is now split into two clear app boundaries:

```text
apps/
  web/                 React + Vite dashboard
  pipeline/            Python agentic news pipeline
data/                  Generated dashboard artifacts
docs/                  Architecture notes
memory/                Project context and handoff notes
```

The backend remains an artifact pipeline, not an API service. The Python pipeline writes `data/output.json` and `data/health.json`; the React dashboard reads those files.

```text
fetch agents
  -> deduplicate
  -> normalize
  -> score
  -> quality gate
  -> summarize
  -> write data/output.json + data/health.json
  -> React dashboard renders the brief
```

## What Exists Today

| Area | Status | Notes |
| --- | --- | --- |
| Monorepo structure | Done | Frontend in `apps/web`, pipeline in `apps/pipeline/src/news_pipeline` |
| React dashboard | Done | Vite + React dashboard reads root `data/output.json` |
| Pipeline entry point | Done | `npm run pipeline` runs `news_pipeline.supervisor` |
| Fetch agents | Done | arXiv, GitHub, and RSS agents are implemented |
| Artifact generation | Done | Pipeline writes `data/output.json` and `data/health.json` |
| Source health logging | Done | Per-source status, count, duration, and errors are captured |
| Basic scoring / quality | Started | Current implementation is functional but still lightweight |
| Summarization | Started | Fallback-style summaries exist; LLM-backed summaries are still future work |
| Trend detection | Placeholder | Module exists, but dashboard-ready trend output still needs implementation |
| Automation | Todo | No scheduled GitHub Actions workflow yet |
| README | Done | Top-level onboarding README added |

## Operating Contract

- `data/output.json` is the main frontend/backend contract.
- The pipeline owns writes to `data/output.json` and `data/health.json`.
- The dashboard only reads generated artifacts and should not call pipeline internals directly.
- Root npm scripts are the preferred entry points:
  - `npm run pipeline`
  - `npm run dev`
  - `npm run build`
  - `npm run preview`

## Next Implementation Priorities

### 1. Strengthen Data Quality

- Improve fuzzy deduplication so related stories from arXiv, RSS, and GitHub collapse cleanly.
- Attach `related_links` when duplicates or cross-source references are found.
- Tighten normalization for missing authors, missing dates, sparse RSS content, and long raw text.
- Make the score easier to explain by breaking it into relevance, keyword, and recency components.

### 2. Improve Dashboard Mapping

- Keep the existing `data/output.json` shape stable for the dashboard.
- Improve section placement so papers, GitHub repos, blogs, tools, and action items map predictably.
- Add a clear generated timestamp and source-health signal in the UI if the design allows it.
- Avoid major visual redesign unless the data contract requires it.

### 3. Add Better Summaries and Trends

- Add optional OpenAI-powered summaries when `OPENAI_API_KEY` is available.
- Keep a no-key fallback so the pipeline remains runnable for every contributor.
- Implement trend detection from repeated keywords/topics across independent sources.
- Write trend data into the existing `trending` array in `data/output.json`.

### 4. Add Automation

- Add a GitHub Actions workflow for manual and scheduled refreshes.
- Install Node and Python dependencies in CI.
- Run the pipeline and commit updated `data/output.json` only when the artifact changes.
- Use repository secrets for `OPENAI_API_KEY` and `GITHUB_TOKEN` when needed.

### 5. Keep Documentation Current

- Keep `README.md` focused on normal project onboarding.
- Keep `docs/architecture.md` focused on repository structure and data flow.
- Keep `memory/` updated after meaningful architecture or workflow changes.

## Recommended Validation

Run these from the repository root after meaningful changes:

```sh
npm run pipeline
PYTHONPATH=apps/pipeline/src python3 -m compileall apps/pipeline/src/news_pipeline
python3 -m ruff check apps/pipeline/src/news_pipeline
npm run build
```

Expected results:

- `npm run pipeline` refreshes `data/output.json` and `data/health.json`.
- Python compile and Ruff checks pass.
- Vite builds the dashboard into `dist/`.
- The dashboard uses generated artifact data, not hardcoded fallback data.

## File Structure

```text
llm-news-artifact/
  apps/
    web/
      index.html
      vite.config.js
      src/
        App.jsx
        main.jsx
        styles.css
        ey-fso-ai-brief.jsx
    pipeline/
      requirements.txt
      src/
        news_pipeline/
          supervisor.py
          config.py
          schema.py
          agents/
            fetch_papers.py
            fetch_github.py
            fetch_rss.py
          dedup.py
          normalize.py
          score.py
          quality_gate.py
          summarize.py
          trends.py
          push_to_artifact.py
          health_log.py
  data/
    output.json
    health.json
  docs/
    architecture.md
  memory/
  AGENTS.md
  IMPLEMENTATION_PLAN.md
  README.md
  package.json
```

## Decisions to Preserve

| Decision | Choice |
| --- | --- |
| Repository layout | Monorepo Lite |
| Frontend | React + Vite |
| Backend mode | Python artifact pipeline |
| Shared contract | Root `data/output.json` |
| Health output | Root `data/health.json` |
| API service | Not part of the current plan |
| Scheduling target | GitHub Actions or similar scheduled runner |
| Local build compatibility | Rollup WASM package alias for Vite builds |

## Open Risks

| Risk | Mitigation |
| --- | --- |
| GitHub API rate limits | Use `GITHUB_TOKEN` locally and in CI |
| RSS feed changes | Log source errors and continue partial runs |
| Low-quality fetched items | Improve scoring, quality gate, and dedupe |
| LLM cost or missing API key | Keep summarization optional with fallback summaries |
| Artifact schema drift | Treat `data/output.json` as the frontend/backend contract |
