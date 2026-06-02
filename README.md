# LLM News Artifact

A small intelligence brief dashboard for tracking AI and LLM updates that matter to financial services teams.

The project combines a React dashboard with a Python news pipeline. The pipeline gathers recent AI/LLM signals from arXiv, GitHub, and RSS feeds, scores and formats them, then writes a JSON artifact that the dashboard renders.

## What It Does

- Fetches recent AI/LLM papers, repositories, releases, and blog updates.
- Ranks papers with generic AI/ML research signals and scores other brief items for relevance.
- Produces a dashboard-ready brief with action items, research, repos, articles, and source health.
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
OPENAI_API_KEY=...    # enables LLM-generated GitHub repo bullets
OPENAI_MODEL=...      # optional; defaults to gpt-5.4-mini
OPENAI_REPO_BRIEF_LIMIT=5  # caps repo summary calls per run
OPENAI_PAPER_SUMMARY_LIMIT=8  # caps optional paper summary calls per run
DATE_WINDOW_DAYS=7    # weekly activity window for news and repo freshness
ARXIV_FALLBACK_WINDOW_DAYS=14  # used only when fewer than 8 recent papers exist
GITHUB_MAX_REPO_AGE_DAYS=90  # only show repos created in this recent horizon
```

Keep secrets in `.env` or your shell environment. Do not commit them.

## Generated Data

The pipeline writes:

- `data/output.json` - dashboard content
- `data/health.json` - source health from the latest run

The React app treats `data/output.json` as read-only generated data.

## More Context

- Architecture: `docs/architecture.md`
- Current plan: `IMPLEMENTATION_PLAN.md`
- Agent handoff notes: `memory/handoff.md`
