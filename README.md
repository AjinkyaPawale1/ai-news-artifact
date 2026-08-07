# LLM News Artifact

A small intelligence brief dashboard for tracking credible, actionable AI and LLM updates for enterprise experimentation.

The project combines a React dashboard with a Python news pipeline. The pipeline gathers recent AI/LLM signals from arXiv, GitHub, and RSS feeds, scores and formats them, then writes a JSON artifact that the dashboard renders.

Public dashboard: https://ajinkyapawale1.github.io/ai-news-artifact/

## What It Does

- Fetches recent AI/LLM papers, repositories, releases, and blog updates.
- Prioritizes enterprise-useful RSS and release signals: decision-relevant AI updates,
  concrete shipped capabilities, verified source links, and no tutorial, customer-story,
  consumer-rollout, or education-announcement noise.
- Ranks papers with generic AI/ML research signals and keeps full paper cards under `Research`.
- Tracks trending GitHub repos, model releases, and AI tools/services in separate drill-down views.
- Shows repo recommended actions and clean release CTAs so each expanded card has a next step.
- Shows a compact `Weekly Snapshot` with one featured paper, repo descriptions, release previews, and source health.
- Lets readers switch between the current brief and the three preceding weekly editions.
- Keeps AI Pulse, Social Pulse, and Enterprise Focus as explicit coming-soon placeholders.
- Keeps the frontend simple: it reads generated data from `data/output.json`.

The brief is enterprise-oriented, not yet personalized. RSS and release selection enforce
enterprise relevance controls, while paper and repository ranking remains a general
research/engineering signal until broader credibility, actionability, and personalization
scoring is implemented.

## Project Layout

```text
apps/web/        React + Vite dashboard
apps/pipeline/   Python news pipeline
data/            Generated output and health artifacts
docs/            Architecture notes
memory/          Project handoff and decision notes
```

## Getting Started

Install the JavaScript dependencies:

```sh
npm install
```

Install the Python pipeline dependencies:

```sh
python3 -m pip install -r apps/pipeline/requirements.txt
```

Refresh the news artifact:

```sh
npm run pipeline
```

Start the dashboard locally:

```sh
npm run dev
```

Vite will print a local URL. Open that URL in your browser to view the dashboard.

## Useful Commands

```sh
npm run pipeline   # fetch and regenerate data/output.json
npm run pipeline:papers   # refresh papers only and preserve other dashboard sections
npm run dev        # start the local dashboard
npm run build      # build the dashboard
npm run preview    # preview the production build
```

## Deployment

The dashboard deploys to GitHub Pages from `main` through
`.github/workflows/deploy-pages.yml`. Pushes build and publish the current artifact.
Every Monday at 10:00 AM America/New_York, the workflow also runs the pipeline, archives
the edition, validates all required source lanes and minimum content, commits generated
artifacts, and publishes the refreshed dashboard. Failed or incomplete runs stop before
commit and deployment, preserving the previously published edition.

Pull requests and feature-branch pushes run `.github/workflows/ci.yml`, which installs
both runtimes, tests, lints, and compiles the Python pipeline, and builds the dashboard.

Local builds use `/` as the Vite base path. Pages builds set `GITHUB_PAGES=true` and use
`/ai-news-artifact/`.

## Optional Environment Variables

The pipeline can run without secrets, but these are useful:

```sh
GITHUB_TOKEN=...      # improves GitHub API rate limits
OPENAI_API_KEY=...    # enables default LLM-generated repo briefs/actions and paper summaries/actions
OPENAI_MODEL=...      # optional; defaults to gpt-5.4-mini
OPENAI_REPO_BRIEF_LIMIT=5  # caps repo brief/action calls per run
OPENAI_PAPER_SUMMARY_LIMIT=8  # caps default paper summary calls per run
OPENAI_PAPER_SUMMARY_MAX_RETRIES=2  # retries transient summary failures twice
DATE_WINDOW_DAYS=7    # weekly activity window for news and repo freshness
MODEL_TOOL_MAJOR_MODEL_WINDOW_DAYS=28  # carry-forward window for high-impact official model launches
MODEL_TOOL_FEED_SCAN_LIMIT=64  # entries inspected per model/tool feed
ARXIV_FALLBACK_WINDOW_DAYS=14  # used only when fewer than 8 recent papers exist
ARXIV_MAX_RETRIES=2   # retries transient category failures twice
ARXIV_REQUEST_INTERVAL_SECONDS=3  # respects arXiv request pacing guidance
GITHUB_MAX_REPO_AGE_DAYS=90  # only show repos created in this recent horizon
```

Keep secrets in `.env` or your shell environment. Do not commit them.

## Suggesting A Source

The dashboard's Pipeline tab lists every source the pipeline currently tracks and links to
a **Suggest a source** issue form (RSS/blog feed, GitHub repository, or model/tool official
page). A maintainer reviews each suggestion and applies the `source-approved` label to
approve it — nothing reaches the pipeline automatically. That label triggers
`.github/workflows/approve-source.yml`, which validates the suggestion and commits it to
`data/user_sources.json`; `apps/pipeline/src/news_pipeline/config.py` and
`model_tools_config.py` merge that file into the pipeline's source lists on the next run.

## Generated Data

The pipeline writes:

- `data/output.json` - dashboard content
- `data/health.json` - source health from the latest run
- `data/archive/YYYY-MM-DD/` - Monday-keyed weekly output and health snapshots
- `data/archive/index.json` - newest-first archive manifest used by the dashboard

The React app treats `data/output.json` as read-only generated data. The current public
contract includes `papers`, `repos`, `models`, `toolsServices`, `blogs`, `socialPosts`,
and additive `fallbackSections` provenance. When a current section has no valid items,
the pipeline may reuse its most recent structurally valid, source-healthy section from
the previous four weeks; the dashboard retains original card dates and labels the reused
section.
The archive manifest is bundled, while individual historical outputs are deployed as
static JSON and downloaded only when a reader selects that edition.

## License

Copyright (c) 2026 Ajinkya Pawale. Released under the [MIT License](LICENSE).

You may use, modify, and redistribute this code, including commercially, as long as the
copyright notice and license text are retained in any copy or substantial portion.

## More Context

- Architecture: `docs/architecture.md`
- Research paper agent: `docs/research-paper-agent-architecture.md`
- GitHub agent: `docs/github-agent-architecture.md`
- Model/tools agent: `docs/model-tools-agent-architecture.md`
- Current plan: `IMPLEMENTATION_PLAN.md`
- Agent handoff notes: `memory/handoff.md`
