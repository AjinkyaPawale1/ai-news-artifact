# Agent Guide: LLM News Artifact

This file is the operating guide for AI coding agents working in this repository.
Read it before making changes, then read the files under `memory/`.

## Purpose
- Build and maintain a weekly enterprise AI intelligence brief dashboard.
- Preserve project context in version-controlled memory so future sessions do not start from zero.
- Keep coding work simple, scoped, verifiable, and aligned with existing architecture.

## Project Snapshot
- Stack: React 18, Vite 5, lucide-react, JSX.
- Frontend app: `apps/web`.
- Main dashboard component: `apps/web/src/ai-intelligence-brief.jsx`.
- App bootstrap: `apps/web/src/main.jsx` and `apps/web/src/App.jsx`.
- Pipeline package: `apps/pipeline/src/news_pipeline`.
- Shared artifacts: `data/output.json`, `data/health.json`, and `data/archive/`.
- Styling: utility classes plus `apps/web/src/styles.css`.

## Runbook
- Install: `npm install`
- Pipeline deps: `pip install -r apps/pipeline/requirements.txt`
- Pipeline: `npm run pipeline`
- Dev server: `npm run dev`
- Build: `npm run build`
- Preview build: `npm run preview`

## Permanent Project Facts
- Use the existing React + Vite frontend unless the user explicitly asks for a stack change.
- Use the existing Python pipeline package under `apps/pipeline/src/news_pipeline`.
- Use LangGraph/LangChain for agent workflow structure in this repo when adding or changing agent flows.
- Keep `data/output.json` and `data/health.json` as the pipeline-to-frontend contract.
- Keep user-facing dashboard copy clean; do not expose internal scoring logic or reasoning text.
- Prefer deterministic labels and summaries where the UI should remain stable.
- Never commit secrets, tokens, API keys, or private credentials.

## Core Coding Principles

### 1. Think Before Coding
- Do not assume hidden context.
- Read relevant files before editing.
- If multiple interpretations exist, present the options before choosing.
- If a requirement is unclear and guessing could cause rework, ask.
- Surface uncertainty, tradeoffs, and risky assumptions before acting on them.

### 2. Simplicity First
- Implement the smallest working solution that satisfies the request.
- Do not add speculative features, abstractions, configurability, or future-proofing.
- Do not introduce a new dependency when local code or existing dependencies are enough.
- If a change becomes much larger than expected, pause and reassess the approach.

### 3. Surgical Changes
- Touch only files, functions, and lines directly related to the task.
- Do not refactor, rename, reformat, or reorganize unrelated code.
- Match the existing local style even when another style seems preferable.
- Clean up imports, variables, and functions made unused by your own change.
- Mention unrelated cleanup opportunities in the final note instead of making drive-by edits.

### 4. Goal-Driven Execution
- For non-trivial tasks, define the intended outcome and verification path before implementation.
- Convert vague work into verifiable goals.
- Prefer tests, builds, compile checks, or focused command validation when available.
- Keep looping until the requested change is implemented and checked, or clearly explain the blocker.

## Planning and Approval Rules
- For significant architecture, workflow, data contract, or UI direction changes, present 2-3 viable paths before editing.
- Ask for explicit approval before destructive actions, broad rewrites, dependency removals, migrations, deployments, publishing, or irreversible external side effects.
- "Previously discussed" is not approval. Approval must be current to the active request.
- If the user says "go ahead" after options were presented, proceed with the recommended path unless they specify otherwise.

## Response Style
- Match answer length to task complexity.
- Skip generic filler and get to the useful answer quickly.
- For simple status questions, verify the machine state directly and answer from evidence.
- For coding tasks, end with what changed, how it was verified, and any important follow-up.
- Do not over-explain project basics the memory files already establish unless the user asks.

## Repository Memory Protocol
All persistent project memory lives in `memory/` and must stay versioned.

1. `memory/context.md`
- Canonical technical context and current architecture.
- Update when architecture, dependencies, entry points, or permanent project facts change.

2. `memory/decisions.md`
- ADR-lite log of meaningful technical and workflow decisions.
- Each entry should state what was decided, why, and the impact.

3. `memory/handoff.md`
- Current status, next actions, known risks, and quick resume instructions.
- Update at the end of each substantial implementation or documentation session.

4. `memory/tasks.md`
- Concise task board with `todo`, `in-progress`, `blocked`, and `done`.
- Keep status aligned with reality.

5. `memory/errors.md`
- Repeated failures, failed approaches, and final working fixes.
- Add an entry when an approach fails more than once or when an error would be useful to avoid later.

## Session Memory Rules
- At session start, read `AGENTS.md` and the relevant files under `memory/`.
- Before proposing a solution for a repeated or suspicious failure, check `memory/errors.md`.
- When the user says "session end", "wrapping up", "let's stop here", or similar, update:
  - `memory/handoff.md` with what changed, what remains, and next priorities.
  - `memory/tasks.md` with current task status.
  - `memory/decisions.md` if a meaningful decision was made.
  - `memory/errors.md` if repeated failures or useful debugging lessons occurred.

## Required Update Checklist
- Update `memory/handoff.md` after substantial work.
- Update `memory/context.md` when architecture, dependencies, entry points, or permanent facts change.
- Append `memory/decisions.md` when a non-trivial choice is made.
- Update `memory/tasks.md` so status matches reality.
- Update `memory/errors.md` when a repeated failure or important troubleshooting lesson occurs.

## Handoff Quality Standard
A new contributor should be able to answer all of these from repo memory:
- What the app does.
- How to run it.
- What changed recently.
- What is currently pending.
- Which tradeoffs were made and why.
- Which approaches failed and should not be repeated.
