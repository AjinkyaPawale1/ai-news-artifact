# Repository Context

Last updated: 2026-05-28

## Purpose
A single-page dashboard UI for a weekly AI intelligence brief tailored to financial services stakeholders.

## Architecture
- Repository style: lightweight monorepo.
- Frontend runtime: Vite + React (ES modules) under `apps/web`.
- Agent pipeline runtime: Python 3 package under `apps/pipeline/src/news_pipeline`.
- Primary dashboard component: `apps/web/src/ey-fso-ai-brief.jsx` (default export Dashboard).
- Dashboard data artifact: `data/output.json`.
- Pipeline health artifact: `data/health.json`.
- Python pipeline entry point: `news_pipeline.supervisor`.
- Fetch agents:
  - `news_pipeline.agents.fetch_papers` for arXiv.
  - `news_pipeline.agents.fetch_github` for GitHub search and releases.
  - `news_pipeline.agents.fetch_rss` for RSS/Atom feeds.
  - `news_pipeline.agents.model_tools_graph` for model release and AI tool/service extraction from RSS-style sources.
- Entry wiring:
  - `apps/web/src/App.jsx` imports Dashboard.
  - `apps/web/src/main.jsx` mounts App to `#root`.
- HTML shell: `apps/web/index.html`.
- Local baseline CSS: `apps/web/src/styles.css`.

## Dependencies
- Frontend: react, react-dom, lucide-react, vite, @vitejs/plugin-react, Rollup WASM package alias
- Pipeline: requests, feedparser, python-dotenv, ruff

## Notes
- Utility-class styling is used in the dashboard component.
- Tailwind utility classes are enabled via CDN script in index.html.
- Dashboard imports generated pipeline data from root `data/output.json`.
- `npm run pipeline` is a convenience wrapper around `PYTHONPATH=apps/pipeline/src python3 -m news_pipeline.supervisor`.
- Architecture details live in `docs/architecture.md`.
- Agent operating guidance now lives in `AGENTS.md`.
- Repository memory includes `memory/errors.md` for repeated failures and troubleshooting lessons.
- `models` and `toolsServices` are generated from classified pipeline items with `source_type` values `model` and `tool_service`.

## Operational Commands
- npm install
- pip install -r apps/pipeline/requirements.txt
- npm run pipeline
- npm run dev
- npm run build
- npm run preview
