"""
Append-only action logger for Vote Uncovered.

All outbound actions (comments, replies, posts) and significant events
are recorded to logs/actions.log with timestamps and capability tags.
"""

import os
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOGS_DIR / "actions.log"


def log_action(capability: str, message: str, **extra):
    """Append a timestamped entry to the action log.

    Args:
        capability: Which part of the pipeline (sync-elections, monitor, post, reply).
        message: Human-readable description of what happened.
        **extra: Additional key=value pairs to include (post_id, comment_id, etc.).
    """
    LOGS_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    parts = [f"[{ts}] [{capability}] {message}"]
    for k, v in extra.items():
        parts.append(f"  {k}: {v}")
    entry = "\n".join(parts) + "\n\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
