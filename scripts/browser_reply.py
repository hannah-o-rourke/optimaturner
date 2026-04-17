#!/usr/bin/env python3
"""
browser_reply.py — Browser-based equivalent of reply.py.

Checks replies on Vote Uncovered's comments using Playwright and responds.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from browser_automation import (
    create_browser_context, login_to_facebook, navigate_to_page,
    read_page_posts, save_browser_state, cleanup, human_delay,
    _nuke_overlays, _dispatch_click,
    FB_PAGE_ID,
)
from reply import (
    HELPFUL_REPLIES, HOSTILE_INDICATORS, POLITE_DISENGAGE,
    classify_reply,
)
from action_logger import log_action

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMENTED_FILE = DATA_DIR / "commented.json"
REPLIED_FILE = DATA_DIR / "replied.json"


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def find_our_comment_and_replies(page, comment_snippet: str) -> list[dict]:
    """Find our comment on the current page and extract replies to it.

    Returns list of reply dicts: {text, author_hint}.
    """
    replies = []

    # Scroll to load comments
    for _ in range(4):
        page.mouse.wheel(0, 500)
        human_delay(1, 2)

    try:
        # Look for our comment text
        snippet = comment_snippet[:40]
        comment_els = page.locator(f'text="{snippet}"').all()

        if not comment_els:
            return replies

        for cel in comment_els:
            # Try to find "View replies" or reply sub-threads near our comment
            try:
                parent = cel.locator("xpath=ancestor::*[5]")
                # Look for "View X replies" button
                reply_btns = parent.locator('text=/[Vv]iew.*repl/').all()
                for btn in reply_btns:
                    try:
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            human_delay(2, 3)
                    except Exception:
                        pass

                # Gather reply text blocks — they appear as sub-items
                # This is inherently fragile with Facebook's DOM, but we do our best
                sub_items = parent.locator('div[role="article"], ul li').all()
                for item in sub_items:
                    try:
                        txt = item.inner_text(timeout=3000).strip()
                        # Skip if it's our own comment
                        if snippet in txt:
                            continue
                        if txt and len(txt) > 5:
                            replies.append({"text": txt[:300], "author_hint": ""})
                    except Exception:
                        continue
            except Exception:
                continue

    except Exception as e:
        log_action("browser-reply", f"ERROR searching for comment replies: {e}")

    return replies


def reply_to_comment(page, reply_text: str, response: str) -> bool:
    """Type a reply to a visible reply in the comment thread.

    This clicks into the reply area and types our response.
    """
    try:
        # Look for the reply box that should be open in the thread
        reply_box_selectors = [
            'div[role="textbox"][aria-label*="reply" i]',
            'div[role="textbox"][aria-label*="Reply" i]',
            'div[role="textbox"][aria-label*="comment" i]',
            'div[contenteditable="true"]',
        ]

        _nuke_overlays(page)

        for sel in reply_box_selectors:
            try:
                box = page.locator(sel).last
                if box.is_visible(timeout=3000):
                    box.click()
                    human_delay(0.5, 1)
                    # Use press_sequentially for Facebook's Lexical editor
                    box.press_sequentially(response, delay=30)
                    human_delay(1, 2)
                    # Submit via JS dispatch (React ignores synthetic clicks)
                    _dispatch_click(page, '[aria-label="Post comment"]')
                    human_delay(2, 4)
                    return True
            except Exception:
                continue

        return False

    except Exception as e:
        log_action("browser-reply", f"ERROR posting reply: {e}")
        return False


def browser_handle_replies(headless: bool = True, dry_run: bool = False):
    """Check all our comments for new replies and respond via browser."""
    commented = load_json(COMMENTED_FILE)
    replied = load_json(REPLIED_FILE)
    if "replies" not in replied:
        replied["replies"] = {}

    posts = commented.get("posts", {})
    if not posts:
        log_action("browser-reply", "No commented posts to check for replies.")
        print("No commented posts to check.")
        return

    replies_sent = 0
    log_action("browser-reply", f"Checking replies on {len(posts)} commented posts")

    pw, browser, context, page = create_browser_context(headless=headless)

    try:
        if not login_to_facebook(page):
            log_action("browser-reply", "ERROR: Login failed")
            print("Login failed.")
            return

        save_browser_state(context)

        # Group comments by page to minimise navigation
        page_comments = {}
        for post_key, info in posts.items():
            page_name = info.get("page", "unknown")
            if page_name not in page_comments:
                page_comments[page_name] = []
            page_comments[page_name].append((post_key, info))

        for page_name, comments in page_comments.items():
            for post_key, info in comments:
                snippet = info.get("post_snippet", "")
                comment_snippet = snippet[:40] if snippet else "vote"

                # We'd need to navigate to the actual post URL
                # For browser-based reply checking, this is inherently limited
                # We log the attempt for the proof of concept
                log_action(
                    "browser-reply",
                    f"Would check replies on {page_name} post: {snippet[:80]}",
                    method="browser",
                    post_key=post_key,
                )

                # In a real deployment, we'd navigate to each post permalink
                # and check for replies. For the POC, we note the limitation.

            human_delay(2, 5)

        save_browser_state(context)

    finally:
        cleanup(pw, browser, context)

    log_action("browser-reply", f"Reply check complete. {replies_sent} replies sent.")
    print(f"Browser reply check complete: {replies_sent} replies sent.")


def main():
    parser = argparse.ArgumentParser(description="Browser-based reply checker")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--dry-run", action="store_true", help="Don't post replies, just log")
    args = parser.parse_args()

    browser_handle_replies(headless=not args.headed, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
