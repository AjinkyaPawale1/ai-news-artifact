# Decision Log

## 2026-05-04 - Use Vite React wrapper for standalone JSX component
Status: accepted

Reason:
- The source file is a React component, not directly executable as a script.
- Vite provides the fastest local dev runtime for JSX with minimal config.

Impact:
- Added package.json, vite.config.js, index.html, and src entry files.
- Project now runs with npm scripts.

## 2026-05-04 - Keep repo-level agent memory under version control
Status: accepted

Reason:
- Future human/AI contributors need deterministic handoff context.
- Versioned memory avoids context loss between sessions.

Impact:
- Added agent.md and memory/* files with update protocol.

## 2026-05-11 - Build agent pipeline in Python and keep frontend in React
Status: accepted

Reason:
- Python is better suited for feed parsing, data processing, scoring, and future LLM/NLP work.
- The existing Vite React dashboard already works well as the frontend.

Impact:
- Added Python pipeline under pipeline/ with supervisor, fetch agents, schema/config, scoring stubs, quality gate, artifact writer, and health logging.
- Added data/output.json as the frontend data artifact.
- Added npm run pipeline as a wrapper for python3 pipeline/supervisor.py.

## 2026-05-14 - Adopt Monorepo Lite structure
Status: accepted

Reason:
- The project has two clear runtimes: React/Vite frontend and Python agentic pipeline.
- A lightweight monorepo boundary keeps those runtimes separate without adding heavy workspace tooling.
- Root `data/output.json` remains the explicit artifact contract between backend and frontend.

Impact:
- Moved the frontend into `apps/web`.
- Moved the Python pipeline into the `news_pipeline` package under `apps/pipeline/src`.
- Kept root npm scripts as the main developer entry points.
- Added `docs/architecture.md` for the current data flow and repository layout.

## 2026-05-14 - Use Rollup WASM package alias for Vite builds
Status: accepted

Reason:
- The local macOS dependency install had native binary launch issues during Vite build validation.
- The WASM-backed Rollup package provides the same Rollup interface without relying on the native Rollup addon.

Impact:
- Added a direct dev dependency alias: `rollup` -> `@rollup/wasm-node`.
- Vite build validation completes successfully from the root npm script.

## 2026-05-15 - Use LangGraph for GitHub repo discovery
Status: accepted

Reason:
- GitHub discovery needs a multi-step agent flow: search, enrich, score, summarize, and emit dashboard items.
- LangGraph keeps that flow explicit and aligns with the project direction for agent structure.
- The pipeline should still run without an OpenAI key.

Impact:
- Added `news_pipeline.agents.github_graph` with a LangGraph StateGraph for repo discovery.
- GitHub items now carry repo metadata, bullets, traction score, latest release, and related links.
- OpenAI-generated repo briefs are optional via `OPENAI_API_KEY`; deterministic bullets remain the fallback.
- The dashboard repo section now expands to show repo details and links out to GitHub.

## 2026-05-20 - Rename agent guide to AGENTS.md and expand operating rules
Status: accepted

Reason:
- `AGENTS.md` is a common repository instruction filename for coding agents.
- The original guide captured repo memory basics but did not fully encode coding-agent behavior, approval rules, repeated-error tracking, or session-end memory updates.
- The updated guide incorporates Karpathy-style coding principles and the X-thread recommendations around memory, scope control, confirmations, and technical-stack locking.

Impact:
- Renamed `agent.md` to `AGENTS.md`.
- Added stricter guidance for thinking before coding, simplicity, surgical changes, and verification.
- Added approval rules for major, destructive, deployment, publishing, and other side-effectful actions.
- Added `memory/errors.md` for repeated failures and troubleshooting lessons.
- Updated repo memory files to reference the expanded protocol.

## 2026-05-28 - Extract model releases and tools/services as classified RSS items
Status: accepted

Reason:
- The dashboard already had compact `models` and `toolsServices` card contracts.
- RSS-style vendor feeds are the lowest-friction source for launch and service announcements.
- A deterministic classifier keeps user-facing copy clean and avoids model-dependent labels for weekly runs.

Impact:
- Added `news_pipeline.agents.model_tools_graph` with a LangGraph workflow and sequential fallback.
- Added `model` and `tool_service` source types and artifact mapping for generated release cards.
- Exact-URL dedupe now preserves specific model/tool classifications over duplicate generic RSS entries.
