#!/usr/bin/env python3
"""
browser_post.py — Browser-based equivalent of post.py.

Generates and publishes daily content to the Vote Uncovered Facebook page
using Playwright instead of the Graph API.
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from browser_automation import (
    create_browser_context, login_to_facebook, post_to_own_page,
    save_browser_state, cleanup, switch_to_page_profile,
    _nuke_overlays,
)
from post import (
    load_elections, generate_post_content, days_until_election,
)
from action_logger import log_action
from comment_logger import log_comment

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
POSTED_FILE = DATA_DIR / "posted.json"


def load_posted() -> dict:
    if POSTED_FILE.exists():
        return json.loads(POSTED_FILE.read_text())
    return {"posts": []}


def save_posted(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    POSTED_FILE.write_text(json.dumps(data, indent=2))


def browser_post_daily(headless: bool = True, dry_run: bool = False):
    """Generate and publish today's post via browser."""
    today = date.today().isoformat()
    posted = load_posted()

    # Check if we already posted today
    if any(p.get("date") == today for p in posted.get("posts", [])):
        log_action("browser-post", f"SKIP: Already posted today ({today})")
        print(f"Already posted today ({today}). Skipping.")
        return

    elections = load_elections()
    if not elections:
        log_action("browser-post", "SKIP: No election data available. Run sync_elections first.")
        print("No election data. Run sync_elections.py first.")
        return

    content = generate_post_content(elections)

    if dry_run:
        log_action("browser-post", f"DRY RUN: Would post to page", post_text=content[:200])
        print(f"[DRY RUN] Would post:\n{content}")
        return

    pw, browser, context, page = create_browser_context(headless=headless)

    try:
        if not login_to_facebook(page):
            log_action("browser-post", "ERROR: Login failed")
            print("Login failed.")
            return

        save_browser_state(context)

        # Switch to page profile before posting
        switch_to_page_profile(page)

        success = post_to_own_page(page, content)

        if success:
            posted["posts"].append({
                "date": today,
                "post_id": f"browser_{datetime.utcnow().isoformat()}",
                "content": content,
                "posted_at": datetime.utcnow().isoformat() + "Z",
                "method": "browser",
            })
            save_posted(posted)

            log_action(
                "browser-post",
                "Published daily post to Vote Uncovered page via browser",
                post_text=content[:200],
            )
            log_comment(
                page_name="Vote Uncovered",
                page_url=f"https://www.facebook.com/{os.getenv('FB_PAGE_ID', 'voteuncovered')}",
                comment_text=content,
                post_url="",
                comment_url="",
            )
            print("Posted to page successfully!")
        else:
            log_action("browser-post", "ERROR: Failed to publish post via browser")
            print("Failed to post. Check logs for details.")

        save_browser_state(context)

    finally:
        cleanup(pw, browser, context)


def main():
    parser = argparse.ArgumentParser(description="Browser-based page poster")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--dry-run", action="store_true", help="Don't post, just show what would be posted")
    args = parser.parse_args()

    browser_post_daily(headless=not args.headed, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
