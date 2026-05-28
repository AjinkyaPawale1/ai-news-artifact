# Error Log

Last updated: 2026-05-28

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

### 2026-05-28 - Python compileall cache permission on macOS
Status: resolved

What failed:
- `python3 -m compileall ...` tried to write bytecode under
  `/Users/ajinkyapawale/Library/Caches/com.apple.python/...` and failed in the sandbox.

What worked:
- Rerun compile/test commands with `PYTHONPYCACHEPREFIX=/private/tmp/llm-news-paper-actions-pycache`.

Notes for next time:
- Use a writable `PYTHONPYCACHEPREFIX` for Python validation commands in sandboxed worktrees.
