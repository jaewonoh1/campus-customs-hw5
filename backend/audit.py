"""Append-only audit trail for the Campus Customs agent team.

Every agent loop step appends one JSON object to output/audit_trail.json: when it
ran, which role, under which parent run, the MCP tools it called (with short
args/results), who it delegated to, how many model calls it made, its answer, and
why it stopped. The file is appended across runs — never wiped — so the whole
history of the team's work is preserved. A corrupt file is moved aside rather
than overwritten, and writes are atomic (temp file then replace).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models import AuditEntry

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_FIELD_CHARS = 300


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def shorten(value: object, limit: int = MAX_FIELD_CHARS) -> str:
    """One-line, length-capped string form of any value, for the log."""
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append_entry(entry: AuditEntry) -> None:
    """Append one step to the trail, creating or recovering the file as needed."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if AUDIT_PATH.exists():
        try:
            loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
            else:
                raise ValueError("audit trail is not a JSON array")
        except (json.JSONDecodeError, ValueError):
            corrupt = AUDIT_PATH.with_suffix(f".corrupt-{utc_now()}.json")
            AUDIT_PATH.rename(corrupt)
            existing = []

    existing.append(entry.model_dump())
    tmp = AUDIT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    tmp.replace(AUDIT_PATH)
