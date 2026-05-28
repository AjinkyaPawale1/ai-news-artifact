"""Source health logging utilities."""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[4] / "data"


def write_health_log(entries: list[dict]) -> None:
    """Write source health results for the latest run."""
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "health.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
