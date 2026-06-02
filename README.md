# LLM News Artifact

A small intelligence brief dashboard for tracking credible, actionable AI and LLM updates for enterprise experimentation.

The project combines a React dashboard with a Python news pipeline. The pipeline gathers recent AI/LLM signals from arXiv, GitHub, and RSS feeds, scores and formats them, then writes a JSON artifact that the dashboard renders.

## What It Does

- Fetches recent AI/LLM papers, repositories, releases, and blog updates.
- Ranks papers with generic AI/ML research signals and keeps full paper cards under `Research`.
- Tracks trending GitHub repos, model releases, and AI tools/services in separate drill-down views.
- Shows a compact `Weekly Snapshot` with one featured paper, repo descriptions, release previews, and source health.
- Keeps AI Pulse, Social Pulse, and Enterprise Focus as explicit coming-soon placeholders.
- Keeps the frontend simple: it reads generated data from `data/output.json`.

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

## Optional Environment Variables

The pipeline can run without secrets, but these are useful:

```sh
GITHUB_TOKEN=...      # improves GitHub API rate limits
OPENAI_API_KEY=...    # enables default LLM-generated repo and paper summaries
OPENAI_MODEL=...      # optional; defaults to gpt-5.4-mini
OPENAI_REPO_BRIEF_LIMIT=5  # caps repo summary calls per run
OPENAI_PAPER_SUMMARY_LIMIT=8  # caps default paper summary calls per run
OPENAI_PAPER_SUMMARY_MAX_RETRIES=2  # retries transient summary failures twice
DATE_WINDOW_DAYS=7    # weekly activity window for news and repo freshness
ARXIV_FALLBACK_WINDOW_DAYS=14  # used only when fewer than 8 recent papers exist
ARXIV_MAX_RETRIES=2   # retries transient category failures twice
ARXIV_REQUEST_INTERVAL_SECONDS=3  # respects arXiv request pacing guidance
GITHUB_MAX_REPO_AGE_DAYS=90  # only show repos created in this recent horizon
```

Keep secrets in `.env` or your shell environment. Do not commit them.

## Generated Data

The pipeline writes:

- `data/output.json` - dashboard content
- `data/health.json` - source health from the latest run

The React app treats `data/output.json` as read-only generated data. The current public
contract includes `papers`, `repos`, `models`, `toolsServices`, `blogs`, and `socialPosts`.

## More Context

- Architecture: `docs/architecture.md`
- Research paper agent: `docs/research-paper-agent-architecture.md`
- GitHub agent: `docs/github-agent-architecture.md`
- Model/tools agent: `docs/model-tools-agent-architecture.md`
- Current plan: `IMPLEMENTATION_PLAN.md`
- Agent handoff notes: `memory/handoff.md`
