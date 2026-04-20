#!/usr/bin/env python3
"""
monitor.py — Watch community Facebook pages and comment on local-issue posts.

Reads config/pages.csv for the list of pages to monitor.
Checks data/commented.json to avoid double-commenting.
Identifies posts about local issues and leaves election reminders.
"""

import csv
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(__file__))

from graph_api import get_page_posts, post_comment, GraphAPIError
from action_logger import log_action
from region import get_region, election_type_for_region, election_label_for_outlet

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
PAGES_CSV = CONFIG_DIR / "pages.csv"
COMMENTED_FILE = DATA_DIR / "commented.json"
ELECTIONS_FILE = DATA_DIR / "elections.json"

# ── Local issue keywords ────────────────────────────────────────────────
LOCAL_ISSUE_KEYWORDS = [
    "council", "councillor", "planning", "housing", "pothole", "bin collection",
    "recycling", "road", "roadworks", "transport", "bus", "parking", "school",
    "library", "park", "playground", "allotment", "local", "community",
    "neighbourhood", "high street", "regeneration", "development", "antisocial",
    "crime", "police", "flooding", "environment", "air quality", "nhs",
    "hospital", "gp surgery", "care home", "social care", "rent", "landlord",
    "tenant", "homelessness", "rough sleeping", "speed limit", "crossing",
    "cycle lane", "footpath", "streetlight",
]

# Words that indicate national/partisan content — skip these posts
SKIP_KEYWORDS = [
    "general election", "westminster", "parliament", "prime minister",
    "downing street", "labour party", "conservative party", "tory", "tories",
    "lib dem", "reform uk", "green party", "snp", "plaid cymru", "sinn fein",
    "dup", "house of commons", "house of lords", "chancellor", "home secretary",
    "starmer", "sunak",
]

# ── Comment templates ───────────────────────────────────────────────────
# These are template strings with a {election_desc} placeholder that gets
# filled based on the page's region (England/Wales/Scotland).
COMMENT_TEMPLATES = [
    (
        "Did you know {election_desc} are coming up in your area? "
        "Your vote really does make a difference — "
        "find out more at whocanivotefor.co.uk 🗳️"
    ),
    (
        "Elections are just around the corner! It only takes a few "
        "minutes to have your say on the issues that matter most in your "
        "community. Check if you're registered at gov.uk/register-to-vote 🗳️"
    ),
    (
        "Issues like this are exactly what elections are about! "
        "If you want to have a say on how things like this are handled, "
        "make sure you're registered to vote. Polling day is "
        "May 7th — find out who's standing at whocanivotefor.co.uk 🗳️"
    ),
    (
        "This is the kind of thing your elected representatives deal with every day. "
        "With {election_desc} coming up on May 7th, it's your chance to pick who represents you. "
        "More info: whocanivotefor.co.uk 🗳️"
    ),
    (
        "Your elected representatives make decisions on issues just like this. "
        "With {election_desc} on May 7th, now's the time to make your voice heard! "
        "Register to vote at gov.uk/register-to-vote 🗳️"
    ),
]


def get_comment_for_outlet(outlet: str) -> str:
    """Pick a random comment template and fill in the region-appropriate election type."""
    template = random.choice(COMMENT_TEMPLATES)
    election_desc = election_label_for_outlet(outlet)
    return template.format(election_desc=election_desc)


def load_commented() -> dict:
    """Load the set of already-commented post IDs."""
    if COMMENTED_FILE.exists():
        return json.loads(COMMENTED_FILE.read_text())
    return {"posts": {}}


def save_commented(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    COMMENTED_FILE.write_text(json.dumps(data, indent=2))


def has_elections() -> bool:
    """Check if we have cached election data with upcoming local ballots."""
    if not ELECTIONS_FILE.exists():
        return False
    try:
        data = json.loads(ELECTIONS_FILE.read_text())
        return data.get("local_ballots", 0) > 0
    except Exception:
        return False


def is_local_issue(text: str) -> bool:
    """Check if post text discusses a local issue."""
    lower = text.lower()
    # Skip national/partisan content
    for kw in SKIP_KEYWORDS:
        if kw in lower:
            return False
    # Must match at least one local keyword
    return any(kw in lower for kw in LOCAL_ISSUE_KEYWORDS)


def extract_page_id_from_url(fb_url: str) -> str:
    """Extract a page username/ID from a Facebook URL.

    e.g. https://www.facebook.com/theliverpoolecho → theliverpoolecho
    """
    path = urlparse(fb_url).path.strip("/")
    # Take first path segment
    return path.split("/")[0] if path else fb_url


def load_pages() -> list[dict]:
    """Load monitored pages from CSV."""
    pages = []
    with open(PAGES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "found" and row.get("facebook_page"):
                pages.append({
                    "outlet": row["outlet"],
                    "page_id": extract_page_id_from_url(row["facebook_page"]),
                    "facebook_url": row["facebook_page"],
                })
    return pages


def monitor():
    """Main monitor loop: scan pages, comment on local-issue posts."""
    if not has_elections():
        log_action("monitor", "SKIP: No election data found. Run sync_elections first.")
        print("No election data. Run sync_elections.py first.")
        return

    pages = load_pages()
    commented = load_commented()
    commented_posts = commented.get("posts", {})
    comments_made = 0

    log_action("monitor", f"Starting monitor run across {len(pages)} pages")

    for page in pages:
        page_id = page["page_id"]
        try:
            posts = get_page_posts(page_id, limit=10)
        except GraphAPIError as e:
            log_action("monitor", f"ERROR reading {page['outlet']} ({page_id}): {e}")
            continue

        for post in posts:
            post_id = post.get("id", "")
            message = post.get("message", "")

            if not message:
                continue

            # Already commented?
            if post_id in commented_posts:
                continue

            # Is it about a local issue?
            if not is_local_issue(message):
                continue

            # Pick a region-aware comment
            comment_text = get_comment_for_outlet(page["outlet"])

            try:
                result = post_comment(post_id, comment_text)
                comment_id = result.get("id", "unknown")

                # Track it
                commented_posts[post_id] = {
                    "comment_id": comment_id,
                    "page": page["outlet"],
                    "commented_at": datetime.utcnow().isoformat() + "Z",
                    "post_snippet": message[:120],
                }
                comments_made += 1

                log_action(
                    "monitor",
                    f"Commented on post by {page['outlet']}",
                    post_id=post_id,
                    comment_id=comment_id,
                    post_snippet=message[:120],
                    comment_text=comment_text,
                    permalink=post.get("permalink_url", "N/A"),
                )

            except GraphAPIError as e:
                log_action("monitor", f"ERROR commenting on {post_id}: {e}")

    commented["posts"] = commented_posts
    save_commented(commented)

    log_action("monitor", f"Monitor run complete. {comments_made} new comments posted.")
    print(f"Monitor complete: {comments_made} comments posted across {len(pages)} pages.")


if __name__ == "__main__":
    monitor()
