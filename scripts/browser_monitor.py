#!/usr/bin/env python3
"""
browser_monitor.py — Browser-based equivalent of monitor.py.

Polls curated list of community Facebook pages using Playwright,
identifies posts about local issues, and comments with election reminders.
"""

import argparse
import csv
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(__file__))

from browser_automation import (
    create_browser_context, login_to_facebook, navigate_to_page,
    read_page_posts, comment_on_post, save_browser_state, cleanup,
    human_delay, _nuke_overlays, _dispatch_click,
)
from monitor import (
    LOCAL_ISSUE_KEYWORDS, SKIP_KEYWORDS, COMMENT_TEMPLATES,
    is_local_issue, extract_page_id_from_url, load_pages, has_elections,
)
from action_logger import log_action

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMENTED_FILE = DATA_DIR / "commented.json"


def load_commented() -> dict:
    if COMMENTED_FILE.exists():
        return json.loads(COMMENTED_FILE.read_text())
    return {"posts": {}}


def save_commented(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    COMMENTED_FILE.write_text(json.dumps(data, indent=2))


def generate_post_key(page_id: str, post_text: str) -> str:
    """Generate a stable key for a post based on page and text content.

    Since browser automation doesn't give us Graph API post IDs, we use
    a hash of the page + first 100 chars of the post text.
    """
    snippet = post_text[:100].strip().lower()
    return f"browser_{page_id}_{hash(snippet) & 0xFFFFFFFF:08x}"


def browser_monitor(headless: bool = True, max_pages: int = 0, dry_run: bool = False):
    """Main browser-based monitor loop."""
    if not has_elections():
        log_action("browser-monitor", "SKIP: No election data found. Run sync_elections first.")
        print("No election data. Run sync_elections.py first.")
        return

    pages = load_pages()
    if max_pages > 0:
        pages = pages[:max_pages]

    commented = load_commented()
    commented_posts = commented.get("posts", {})
    comments_made = 0

    log_action("browser-monitor", f"Starting browser monitor run across {len(pages)} pages")

    pw, browser, context, page = create_browser_context(headless=headless)

    try:
        if not login_to_facebook(page):
            log_action("browser-monitor", "ERROR: Login failed")
            print("Login failed. Check credentials in .env")
            return

        save_browser_state(context)

        for page_info in pages:
            page_id = page_info["page_id"]
            outlet = page_info["outlet"]

            log_action("browser-monitor", f"Checking {outlet} ({page_id})")

            if not navigate_to_page(page, page_id):
                log_action("browser-monitor", f"SKIP: Could not navigate to {outlet}")
                continue

            posts = read_page_posts(page, max_posts=10)

            for post_data in posts:
                post_text = post_data["text"]
                post_key = generate_post_key(page_id, post_text)

                # Already commented?
                if post_key in commented_posts:
                    continue

                # Is it about a local issue?
                if not is_local_issue(post_text):
                    continue

                # Pick a comment
                comment_text = random.choice(COMMENT_TEMPLATES)

                if dry_run:
                    log_action(
                        "browser-monitor",
                        f"DRY RUN: Would comment on post by {outlet}",
                        post_snippet=post_text[:120],
                        comment_text=comment_text,
                    )
                    print(f"[DRY RUN] Would comment on {outlet}: {post_text[:80]}...")
                    continue

                success = comment_on_post(page, post_data["post_index"], comment_text)

                if success:
                    commented_posts[post_key] = {
                        "comment_id": f"browser_{datetime.utcnow().isoformat()}",
                        "page": outlet,
                        "commented_at": datetime.utcnow().isoformat() + "Z",
                        "post_snippet": post_text[:120],
                        "method": "browser",
                    }
                    comments_made += 1

                    log_action(
                        "browser-monitor",
                        f"Commented on post by {outlet}",
                        post_key=post_key,
                        post_snippet=post_text[:120],
                        comment_text=comment_text,
                    )
                else:
                    log_action("browser-monitor", f"Failed to comment on post by {outlet}")

                # Be respectful of rate — don't comment too fast
                human_delay(5, 15)

            # Pause between pages
            human_delay(3, 8)

        commented["posts"] = commented_posts
        save_commented(commented)

        save_browser_state(context)

    finally:
        cleanup(pw, browser, context)

    log_action("browser-monitor", f"Monitor run complete. {comments_made} new comments posted.")
    print(f"Browser monitor complete: {comments_made} comments posted across {len(pages)} pages.")


def main():
    parser = argparse.ArgumentParser(description="Browser-based Facebook page monitor")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode (visible browser)")
    parser.add_argument("--max-pages", type=int, default=0, help="Limit number of pages to check (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually post comments, just log")
    args = parser.parse_args()

    browser_monitor(headless=not args.headed, max_pages=args.max_pages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
