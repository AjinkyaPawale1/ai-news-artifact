"""Validate and apply a maintainer-approved source suggestion.

Invoked by .github/workflows/approve-source.yml after a maintainer applies the
`source-approved` label to an issue opened via the "Suggest a source" issue
form. Parses the issue body, validates the submitted value, and updates
data/user_sources.json in place. Never touches the file on a validation
failure.

Usage: python apply_user_source.py <issue_body_file> <user_sources_json_path>
Writes `status` and `message` to $GITHUB_OUTPUT when set, and always exits 0
so the calling workflow can comment on the issue either way.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

SOURCE_TYPE_TO_KEY = {
    "rss / blog feed": "rss_feeds",
    "github repository": "github_repos",
    "model or tool official page": "model_tool_pages",
}

FIELD_LABELS = ["Source type", "URL or owner/repo", "Why is this relevant?"]


def parse_issue_body(body: str) -> dict[str, str]:
    """Parse a GitHub issue-form body of repeated '### Label\\n\\nvalue' sections."""
    fields: dict[str, str] = {}
    sections = re.split(r"^### +(.+?) *$", body, flags=re.MULTILINE)
    # re.split with a capturing group yields: [pre, label, value, label, value, ...]
    for i in range(1, len(sections) - 1, 2):
        label = sections[i].strip()
        value = sections[i + 1].strip()
        if label in FIELD_LABELS:
            fields[label] = value
    return fields


def validate(source_key: str, value: str) -> str | None:
    """Return an error message, or None if `value` is valid for `source_key`."""
    if source_key == "github_repos":
        if not REPO_PATTERN.match(value):
            return f"`{value}` doesn't look like an `owner/repo` GitHub repository."
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return f"`{value}` doesn't look like a valid http(s) URL."
    return None


def write_output(status: str, message: str) -> None:
    print(f"{status}: {message}")
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"status={status}\n")
        delimiter = "SOURCE_MSG_EOF"
        handle.write(f"message<<{delimiter}\n{message}\n{delimiter}\n")


def main() -> int:
    if len(sys.argv) != 3:
        write_output("rejected", "Internal error: script called with the wrong number of arguments.")
        return 0

    body_path, sources_path = Path(sys.argv[1]), Path(sys.argv[2])
    body = body_path.read_text(encoding="utf-8")
    fields = parse_issue_body(body)

    source_type = fields.get("Source type", "").strip().lower()
    value = fields.get("URL or owner/repo", "").strip()

    source_key = SOURCE_TYPE_TO_KEY.get(source_type)
    if source_key is None:
        write_output("rejected", f"Could not recognize the source type `{fields.get('Source type', '')}`.")
        return 0
    if not value:
        write_output("rejected", "No URL or repository value was submitted.")
        return 0

    error = validate(source_key, value)
    if error:
        write_output("rejected", error)
        return 0

    data = {"rss_feeds": [], "github_repos": [], "model_tool_pages": []}
    if sources_path.exists():
        try:
            loaded = json.loads(sources_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except json.JSONDecodeError:
            pass

    existing = data.setdefault(source_key, [])
    if value in existing:
        write_output("approved", f"`{value}` is already tracked — nothing to add.")
        return 0

    existing.append(value)
    existing.sort()
    sources_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_output("approved", f"Added `{value}` to `{source_key}`. It will be picked up on the next pipeline run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
