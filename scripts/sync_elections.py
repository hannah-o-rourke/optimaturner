#!/usr/bin/env python3
"""
sync_elections.py — Fetch and cache upcoming UK local election data.

Pulls from whocanivotefor.co.uk and writes to data/elections.json.
Run daily before monitor and post.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(__file__))

from election_data import get_upcoming_ballots
from action_logger import log_action

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ELECTIONS_FILE = DATA_DIR / "elections.json"


def sync():
    DATA_DIR.mkdir(exist_ok=True)

    log_action("sync-elections", "Starting election data sync")

    try:
        ballots = get_upcoming_ballots(limit=200)
    except Exception as e:
        log_action("sync-elections", f"ERROR fetching ballots: {e}")
        raise

    # Filter to local elections only (ballot IDs starting with 'local.')
    local_ballots = [b for b in ballots if b.get("ballot_paper_id", "").startswith("local.")]

    payload = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "total_ballots": len(ballots),
        "local_ballots": len(local_ballots),
        "ballots": local_ballots,
    }

    ELECTIONS_FILE.write_text(json.dumps(payload, indent=2))

    log_action(
        "sync-elections",
        f"Synced {len(local_ballots)} local ballots "
        f"(of {len(ballots)} total) → {ELECTIONS_FILE.name}"
    )

    return payload


if __name__ == "__main__":
    result = sync()
    print(f"Synced {result['local_ballots']} local ballots.")
