# Repository Context

Last updated: 2026-06-02

## Purpose
A single-page dashboard UI for a weekly enterprise AI intelligence brief focused on credible, actionable signals.

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
  - `news_pipeline.agents.paper_graph` for deterministic paper action metadata.
  - `news_pipeline.agents.fetch_github` for GitHub search and releases.
  - `news_pipeline.agents.fetch_rss` for RSS/Atom feeds.
  - `news_pipeline.agents.model_tools_graph` for model release and AI tool/service extraction from RSS-style sources.
  - `news_pipeline.agents.model_tools_dynamic` for bounded LLM-assisted emerging feed and keyword refresh.
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
- The neutral dashboard shell uses six tabs: Weekly Snapshot, Research, Repos, Releases,
  Signals, and Pipeline. Weekly Snapshot is intentionally compact; full lists live in
  drill-down tabs.
- Weekly Snapshot uses a full-width featured-paper banner followed by equal-width repo,
  model-release, and tool/service previews. Repo previews include a one-line description.
- GitHub `bestFor` labels separate knowledge-management products, MCP tooling, and
  retrieval-specific RAG infrastructure; generic `context` mentions do not imply RAG.
- AI Pulse, Social Pulse, and Enterprise Focus are explicit placeholders until their
  collection and ranking workflows are ready.
- `npm run pipeline` is a convenience wrapper around `PYTHONPATH=apps/pipeline/src python3 -m news_pipeline.supervisor`.
- Architecture details live in `docs/architecture.md`.
- Agent operating guidance now lives in `AGENTS.md`.
- Repository memory includes `memory/errors.md` for repeated failures and troubleshooting lessons.
- `models` and `toolsServices` are generated from classified pipeline items with `source_type` values `model` and `tool_service`.
- Model/tool release discovery uses protected official core feeds, official source pages for providers without reliable RSS, plus bounded emerging feeds/terms; OpenAI can propose updates when `OPENAI_API_KEY` is present, but static fallbacks remain.
- Human-maintained model/tool source groups, core terms, and limits live in `apps/pipeline/src/news_pipeline/model_tools_config.py`; `data/model_tools_dynamic_config.json` is generated runtime state for inspection.
- Model/tool vocabulary is standardized: core feeds are always active, emerging feeds/terms rotate within bounds, and candidate feeds are the allowed proposal pool.
- `MODEL_TOOL_MAX_ITEMS` is the single per-category cap for graph selection and dashboard release-card rendering.
- Model/tool dashboard cards include release links plus source feed/page links, and source-page candidates are enriched from official article excerpts before LLM classification where possible.
- Model/tool classification rejects tutorial, guide, case-study, and broad marketing
  headlines unless they clearly announce a release. Selection also collapses same-day,
  same-organization near-duplicate product names while preserving distinct versions.
- RSS selection rotates across configured official feeds before applying the global cap;
  RSS health diagnostics include per-feed fetched, eligible, and selected counts.
- arXiv papers carry deterministic generic AI/ML research metadata in `Item.metadata`,
  including capability, descriptive domain, priority, takeaways, action items, tags,
  `research_score`, visible research signals, and `has_code`.
- Paper ranking is independent from the shared relevance score: research cards are sorted
  by a transparent `0-100` research score and the top eight available papers are emitted.
- Paper fetch diagnostics preserve partial arXiv results and capture per-category status,
  request attempts, retries, plus raw, seven-day, deduplicated, and displayed counts.
- Paper selection uses the seven-day window first and backfills only missing display slots
  from days 8-14 when fewer than eight unique recent papers are available.
- Displayed papers carry exactly three abstract-grounded summary bullets. OpenAI Responses
  API summaries run by default when `OPENAI_API_KEY` is available, retry transient failures
  twice, and fall back to deterministic abstract bullets.
- The weekly snapshot features one ranked paper. The retained `actionItems` artifact
  compatibility field remains derived from ranked papers only, never GitHub or RSS.
- `npm run pipeline:papers` refreshes papers and paper health diagnostics while preserving
  non-paper dashboard sections from the existing artifact checkpoint.
- Research-paper agent details live in `docs/research-paper-agent-architecture.md`,
  including paced arXiv extraction, the three-node LangGraph state, research scoring,
  default OpenAI summary bullets, retries, diagnostics, and artifact mapping.

## Operational Commands
- npm install
- pip install -r apps/pipeline/requirements.txt
- npm run pipeline
- npm run pipeline:papers
- npm run dev
- npm run build
- npm run preview
