"""
Comment logger for Vote Uncovered.

Appends every comment and page post to logs/comments.csv for Electoral
Commission audit trail.  Creates the CSV with headers if it doesn't exist.
"""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
CSV_FILE = LOGS_DIR / "comments.csv"

FIELDNAMES = [
    "timestamp",
    "page_name",
    "page_url",
    "post_url",
    "comment_text",
    "comment_url",
]


def _ensure_csv():
    """Create the CSV with headers if it doesn't already exist."""
    LOGS_DIR.mkdir(exist_ok=True)
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
            writer.writeheader()


def log_comment(
    page_name: str,
    page_url: str,
    comment_text: str,
    post_url: str = "",
    comment_url: str = "",
):
    """Append a row to comments.csv.

    Args:
        page_name:    Human-readable page name (e.g. "Liverpool Echo").
        page_url:     Facebook URL of the page.
        comment_text: The full text of the comment we posted.
        post_url:     Permalink to the post commented on (if available).
        comment_url:  Permalink to our comment (if available).
    """
    _ensure_csv()
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "page_name": page_name,
            "page_url": page_url,
            "post_url": post_url,
            "comment_text": comment_text,
            "comment_url": comment_url,
        })
