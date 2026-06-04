# Error Log

Last updated: 2026-06-04

Use this file for repeated failures, failed approaches, and final working fixes.
Before proposing a solution for a similar issue later, check this file.

## Template

### YYYY-MM-DD - Short issue title
Status: resolved | unresolved

What failed:
- Describe the command, approach, or assumption that did not work.

What worked:
- Describe the final successful approach, if known.

Notes for next time:
- Capture the lesson that should affect future work.

## Entries

### 2026-05-28 - OpenAI API insufficient quota during model/tools refresh
Status: unresolved externally, handled in code

What failed:
- `/v1/models` authenticated successfully with the copied project API key, but `/v1/responses` returned `429` with `code: insufficient_quota` for both the configured model and `gpt-4o-mini`.
- ChatGPT Plus billing does not imply API quota; the API platform needs separate billing/credits.

What worked:
- Added diagnostics that preserve the OpenAI error code/status in model/tools dynamic config.
- The model/tools agent now skips later LLM classification calls when dynamic refresh already reports quota/auth failure.

Notes for next time:
- Check API billing/credits in the OpenAI Platform when `insufficient_quota` appears; code retries or smaller models will not fix account-level quota exhaustion.

### 2026-05-28 - Python compileall cache permission on macOS
Status: resolved

What failed:
- `python3 -m compileall ...` tried to write bytecode under
  `/Users/ajinkyapawale/Library/Caches/com.apple.python/...` and failed in the sandbox.

What worked:
- Rerun compile/test commands with `PYTHONPYCACHEPREFIX=/private/tmp/llm-news-paper-actions-pycache`.

Notes for next time:
- Use a writable `PYTHONPYCACHEPREFIX` for Python validation commands in sandboxed worktrees.

### 2026-06-04 - Vite production build hangs at transforming
Status: resolved

What failed:
- `npm run build` repeatedly reached `vite v5.4.21 building for production...`
  and then timed out at `transforming...`.
- Clearing quarantine metadata with `xattr -dr com.apple.quarantine node_modules`
  did not resolve this occurrence.

What worked:
- The already-running Vite dev server on `http://localhost:5173` rendered the changed
  dashboard, and temporary Playwright screenshots/click checks validated the affected
  Repos and Releases tabs.
- Focused Python artifact tests still passed.
- Removing runtime `cdn.tailwindcss.com` and Google Fonts imports made the dashboard
  self-contained; after that, `npm run build` completed in 1.87s.

Notes for next time:
- Do not reintroduce runtime styling/font CDNs for this dashboard. Keep utilities local
  or move to a real local Tailwind build pipeline if the utility surface grows.

### 2026-06-04 - Vite dev server listens but requests hang
Status: resolved

What failed:
- `npm run dev` left a Vite process listening on `5173`, but `/` and
  `/src/ey-fso-ai-brief.jsx` requests timed out with no HTTP status.
- Killing and restarting with `--force` was not enough while the orphaned Vite/esbuild
  process still held the port.
- Browser automation also exposed a loopback mismatch: Vite was listening on IPv6
  loopback while `127.0.0.1` was refused.

What worked:
- Kill orphaned Vite/esbuild processes, clear `node_modules/.vite`, and restart one
  dev server.
- Remove `@vitejs/plugin-react` from `apps/web/vite.config.js` and let Vite/esbuild
  handle JSX natively.
- Pin Vite dev server host to `127.0.0.1`.
- Import the small set of Lucide icons directly from `lucide-react/dist/esm/icons/...`
  instead of the package barrel so Vite/esbuild does not crawl the full icon catalog
  during dev dependency optimization.
- Clean up old headless Chrome automation processes that were still pointed at the
  dashboard.

Notes for next time:
- If `lsof -iTCP:5173` shows Vite listening but `/usr/bin/curl http://127.0.0.1:5173/`
  hangs, look for orphaned Vite/esbuild PIDs first.
- Do not run a production build check in parallel with the dev server while diagnosing
  this; concurrent esbuild services made the symptom harder to read.
- After the Lucide direct-import change, normal cached `npm run dev` startup measured
  about 130-184 ms, `/` responded in about 68 ms, and the main dashboard JSX module
  responded in about 32 ms. A forced dependency rebuild can still take much longer.
