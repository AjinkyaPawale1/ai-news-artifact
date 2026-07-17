# LLM News Artifact - Implementation Plan

**Updated:** 2026-07-17
**Repository shape:** Monorepo Lite
**Goal:** Maintain a neutral `AI Intelligence Brief` dashboard backed by a Python artifact
pipeline that keeps enterprise users current on credible, actionable AI developments.

## Current Architecture

```text
apps/
  web/                 React + Vite dashboard
  pipeline/            Python agentic artifact pipeline
data/                  Generated dashboard artifacts
docs/                  Architecture notes
memory/                Project context and handoff notes
```

The backend is an artifact pipeline, not an API service. The pipeline writes
`data/output.json` and `data/health.json`; the React dashboard imports the generated
artifact.

```text
parallel fetch agents
  -> deduplicate
  -> normalize
  -> score and gate
  -> summarize/enrich
  -> fill empty sections from eligible prior editions
  -> write data/output.json + data/health.json + weekly archive
  -> React dashboard renders the brief
```

## What Exists Today

| Area | Status | Notes |
| --- | --- | --- |
| React dashboard | Done | Six tabs: Weekly Snapshot, Research, Repos, Releases, Signals, Pipeline |
| Weekly Snapshot | Done | Full-width featured paper banner plus equal-width repo/model/tool previews |
| Research papers | Done | arXiv seven-day-first ranking, 14-day backfill, paper-only refresh path |
| GitHub repos | Done | LangGraph discovery with dynamic queries, repo summaries/actions, and deterministic `bestFor` labels |
| Model/tool releases | Done | Official feeds/source pages, headline release checks, bounded LLM classification, and release/model-directory CTAs |
| RSS articles | Done | Official feed collection with editorial relevance, canonical-summary recovery, verified links, and feed diagnostics |
| Placeholder streams | Done | AI Pulse, Social Pulse, and Enterprise Focus render as coming-soon placeholders |
| Artifact generation | Done | Stable contract, four-week section fallbacks with provenance, source health, and weekly archives |
| GitHub Pages | Done | Static dashboard deploys from `main` to `https://ajinkyapawale1.github.io/ai-news-artifact/` |
| Scheduled refresh automation | Done | Monday 10:00 AM America/New_York refresh, validation, archive commit, and Pages deployment |

## Artifact Contract

The current dashboard contract preserves these top-level arrays:

- `papers`
- `repos`
- `models`
- `toolsServices`
- `blogs`
- `socialPosts`
- `fallbackSections` (additive provenance for reused sections)

Snapshot stats describe the generated artifact directly:

- `PAPERS REVIEWED`
- `REPOS INDEXED`
- `RELEASES TRACKED`
- `HEALTHY SOURCES`

## Current Implementation Priorities

### 1. Broader Enterprise Scoring

- Design credibility, actionability, and personalization scoring before coding.
- Keep this separate from the already implemented release-noise and RSS-fairness fixes.
- Avoid exposing internal scoring rationale in user-facing dashboard copy.

### 2. Cross-Source Linking And Deduplication

- Improve fuzzy deduplication across RSS, GitHub, and papers.
- Add `related_links` when independent sources reference the same repo, paper, release, or provider announcement.
- Extract explicit GitHub/code links from paper metadata or paper pages so `has_code` is link-backed.

### 3. Source Coverage And Quality

- Review `data/model_tools_dynamic_config.json` after weekly runs and tune candidate feeds only when low-yield patterns repeat.
- Add provider-specific source-page extraction when official vendor pages produce sparse or generic text.
- Preserve recent-date requirements for model/tool cards unless a stronger filtering strategy replaces them.

### 4. Automation

- Keep the existing GitHub Pages workflow publishing the static dashboard from `main`.
- Maintain the Monday refresh gate: a new edition must have healthy required sources,
  non-empty dashboard sections, and valid four-week fallback provenance when reuse occurs.
- Configure `GITHUB_TOKEN` for scheduled runs so GitHub rate limiting does not reduce
  repository enrichment coverage.
- Run the pipeline and commit updated generated artifacts only when the artifact changes.
- Use repository secrets for `OPENAI_API_KEY` and `GITHUB_TOKEN` when needed.

## Recommended Validation

Run these from the repository root after meaningful changes:

```sh
PYTHONPATH=apps/pipeline/src python -m unittest discover -s apps/pipeline/tests -v
PYTHONPYCACHEPREFIX=/private/tmp/llm-news-artifact-pycache python -m compileall -q apps/pipeline/src apps/pipeline/tests
git diff --check
npm run build
```

When changing live source behavior, also run:

```sh
npm run pipeline
```

Expected results:

- Unit tests pass.
- Python compile passes.
- Vite builds the dashboard into `dist/`.
- `npm run pipeline` refreshes `data/output.json` and `data/health.json`.
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
        ai-intelligence-brief.jsx
    pipeline/
      requirements.txt
      tests/
      src/
        news_pipeline/
          supervisor.py
          config.py
          schema.py
          agents/
            fetch_papers.py
            fetch_github.py
            fetch_rss.py
            github_graph.py
            model_tools_graph.py
            paper_graph.py
          dedup.py
          normalize.py
          score.py
          quality_gate.py
          push_to_artifact.py
          health_log.py
  data/
    output.json
    health.json
  docs/
    architecture.md
    github-agent-architecture.md
    model-tools-agent-architecture.md
    research-paper-agent-architecture.md
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
| Dashboard shell | Neutral `AI Intelligence Brief` |
| Public Pages URL | `https://ajinkyapawale1.github.io/ai-news-artifact/` |
| Placeholder streams | AI Pulse, Social Pulse, Enterprise Focus stay explicit coming-soon areas |
| Paper selection | Seven-day-first, bounded 14-day backfill |
| Repo labels | Deterministic taxonomy; no broad `context` -> RAG fallback |
| Release selection | Concrete release headlines; reject tutorials/guides/case studies unless clearly announcing a release |
| Scheduling target | GitHub Actions or similar scheduled runner |

## Open Risks

| Risk | Mitigation |
| --- | --- |
| GitHub API rate limits | Use `GITHUB_TOKEN` locally and in CI |
| RSS feed changes | Log source errors and continue partial runs |
| Low-quality fetched items | Continue improving scoring, quality gate, and dedupe |
| LLM cost or missing API key | Keep LLM classification and summaries bounded with deterministic fallbacks |
| Artifact schema drift | Treat `data/output.json` as the frontend/backend contract |
