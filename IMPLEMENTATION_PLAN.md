# LLM News Artifact - Implementation Plan

**Updated:** 2026-07-20
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
| Placeholder streams | Done | AI Pulse and Social Pulse render as coming-soon placeholders; Enterprise Focus now ranks real items by enterprise score |
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

- Step 1 shipped (2026-08-02): deterministic `enterprise_score` with
  adoption/efficiency/governance/evidence components, exposed as `enterpriseScore` on
  cards and surfaced via card badges and the Enterprise Focus panel.
- Preserve the current enterprise-oriented baseline: decision-relevant, verified RSS
  cards and concrete enterprise release/availability headlines.
- Design organization-specific credibility, actionability, and personalization scoring
  before applying an enterprise rank to papers and repositories.
- Keep this separate from the already implemented release-noise, RSS-quality, and
  section-fallback controls.
- Avoid exposing internal scoring rationale in user-facing dashboard copy.

### 2. Cross-Source Linking And Deduplication

- Canonical URL and conservative fuzzy-title deduplication now covers compatible paper,
  repository, and release families without merging short generic titles.
- Duplicate source URLs are retained in `related_links`, and shared normalization removes
  invalid, primary-URL, and repeated related links.
- Extract explicit GitHub/code links from paper metadata or paper pages so `has_code` is link-backed.

### 3. Source Coverage And Quality

- Major versioned model launches from official providers use a conservative 28-day
  carry-forward window when their headlines signal flagship/frontier importance or broad
  availability. Ordinary model and tool/service updates remain on the seven-day window.
- Major model families are ranked ahead of lower-impact release noise, and a later launch
  supersedes an earlier preview for the same family.
- Review `data/model_tools_dynamic_config.json` after weekly runs and tune candidate feeds only when low-yield patterns repeat.
- Add provider-specific source-page extraction when official vendor pages produce sparse or generic text.
- Preserve the seven-day default and the explicit 28-day major-model exception; do not
  widen either window without a source-quality and ranking review.

### 4. Automation

- Pull requests and feature-branch pushes run Python tests, Ruff, compile checks, and the
  Vite production build through `.github/workflows/ci.yml`.
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
| Placeholder streams | AI Pulse and Social Pulse stay explicit coming-soon areas; Enterprise Focus is live |
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
