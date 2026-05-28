# Error Log

Last updated: 2026-05-20

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
