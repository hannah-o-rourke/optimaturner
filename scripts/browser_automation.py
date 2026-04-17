#!/usr/bin/env python3
"""
browser_automation.py — Playwright-based Facebook automation for Vote Uncovered.

Provides core browser primitives: login, navigate to pages, read posts,
comment on posts, check replies, and post to the Vote Uncovered page.

This is a PROOF OF CONCEPT for an Electoral Commission submission
demonstrating how automated social media campaigning works.
It will ONLY be tested against the Vote Uncovered page.
"""

import argparse
import json
import os
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PwTimeout

sys.path.insert(0, os.path.dirname(__file__))
from action_logger import log_action

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BROWSER_STATE_FILE = DATA_DIR / "browser_state.json"

load_dotenv(PROJECT_ROOT / ".env")

FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASSWORD = os.getenv("FB_PASSWORD", "")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "voteuncovered")

# Delays to appear human-like (seconds)
MIN_DELAY = 1.5
MAX_DELAY = 4.0


def human_delay(minimum: float = MIN_DELAY, maximum: float = MAX_DELAY):
    """Sleep a random human-like interval."""
    time.sleep(random.uniform(minimum, maximum))


def _dismiss_cookie_dialog(page: Page):
    """Dismiss Facebook cookie/consent dialogs if present."""
    selectors = [
        '[role="button"]:has-text("Allow all cookies")',
        '[role="button"]:has-text("Accept all")',
        'button[data-cookiebanner="accept_button"]',
        'button[title="Allow all cookies"]',
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept all")',
        '[aria-label="Allow all cookies"]',
    ]
    for sel in selectors:
        try:
            els = page.locator(sel).all()
            for btn in els:
                if btn.is_visible(timeout=2000):
                    btn.click()
                    log_action("browser", "Dismissed cookie consent dialog")
                    human_delay(2, 4)
                    return
        except Exception:
            continue


def _dismiss_popups(page: Page):
    """Dismiss various Facebook popups (notifications, login prompts, etc.)."""
    dismiss_selectors = [
        '[aria-label="Close"]',
        '[aria-label="Decline optional cookies"]',
        'div[role="dialog"] button:has-text("Not Now")',
        'div[role="dialog"] button:has-text("Not now")',
        'div[role="dialog"] [role="button"]:has-text("Not now")',
        'div[role="dialog"] [role="button"]:has-text("OK")',
        'div[role="dialog"] [aria-label="Close"]',
    ]
    for sel in dismiss_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                human_delay(0.5, 1.5)
        except Exception:
            continue


def create_browser_context(headless: bool = True) -> tuple:
    """Create a Playwright browser context, restoring saved state if available.

    Returns (playwright, browser, context, page).
    """
    pw = sync_playwright().start()

    launch_args = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    }

    browser = pw.chromium.launch(**launch_args)

    # Restore saved state if available
    storage_state = None
    if BROWSER_STATE_FILE.exists():
        try:
            storage_state = str(BROWSER_STATE_FILE)
            log_action("browser", "Restoring saved browser state")
        except Exception:
            storage_state = None

    context_opts = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "locale": "en-GB",
        "timezone_id": "Europe/London",
    }
    if storage_state:
        context_opts["storage_state"] = storage_state

    context = browser.new_context(**context_opts)
    page = context.new_page()

    return pw, browser, context, page


def save_browser_state(context: BrowserContext):
    """Save cookies and storage state for session persistence."""
    DATA_DIR.mkdir(exist_ok=True)
    context.storage_state(path=str(BROWSER_STATE_FILE))
    log_action("browser", "Saved browser state to data/browser_state.json")


def login_to_facebook(page: Page) -> bool:
    """Log into Facebook using credentials from .env.

    Returns True if login succeeded, False otherwise.
    """
    if not FB_EMAIL or not FB_PASSWORD:
        log_action("browser", "ERROR: FB_EMAIL or FB_PASSWORD not set in .env")
        return False

    log_action("browser", "Navigating to Facebook login")
    page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
    human_delay(2, 4)

    _dismiss_cookie_dialog(page)

    # Check if already logged in
    if _is_logged_in(page):
        log_action("browser", "Already logged in (session restored)")
        return True

    # Fill login form
    try:
        email_input = page.locator('input[name="email"]').first
        email_input.fill(FB_EMAIL)
        human_delay(0.5, 1.5)

        pass_input = page.locator('input[name="pass"]').first
        pass_input.fill(FB_PASSWORD)
        human_delay(0.5, 1.0)

        # Click login button (Facebook uses role=button divs)
        login_btn = page.locator(
            '[role="button"]:has-text("Log in"), '
            'button[name="login"], button[type="submit"]'
        ).first
        login_btn.click()

        log_action("browser", "Submitted login form")
        human_delay(4, 7)

        _dismiss_cookie_dialog(page)
        _dismiss_popups(page)

    except Exception as e:
        log_action("browser", f"ERROR during login: {e}")
        return False

    if _is_logged_in(page):
        log_action("browser", "Login successful")
        return True
    else:
        log_action("browser", "Login may have failed — could not confirm logged-in state")
        return False


def _is_logged_in(page: Page) -> bool:
    """Check whether we appear to be logged in."""
    indicators = [
        '[aria-label="Your profile"]',
        '[aria-label="Account"]',
        '[aria-label="Facebook"]',
        'a[href*="/me"]',
        '[role="banner"] [role="navigation"]',
        'div[role="navigation"]',
    ]
    for sel in indicators:
        try:
            if page.locator(sel).first.is_visible(timeout=2000):
                return True
        except Exception:
            continue
    # Also check URL — logged-in users don't stay on login page
    return "/login" not in page.url and "facebook.com" in page.url and page.url != "https://www.facebook.com/"


def navigate_to_page(page: Page, page_id: str) -> bool:
    """Navigate to a Facebook page and wait for it to load.

    Args:
        page_id: Facebook page username or ID (e.g. 'theliverpoolecho').

    Returns True if navigation succeeded.
    """
    url = f"https://www.facebook.com/{page_id}"
    log_action("browser", f"Navigating to {url}")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        human_delay(3, 5)
        _dismiss_popups(page)
        return True
    except Exception as e:
        log_action("browser", f"ERROR navigating to {page_id}: {e}")
        return False


def read_page_posts(page: Page, max_posts: int = 10) -> list[dict]:
    """Read recent posts from the currently loaded Facebook page.

    Returns a list of dicts with keys: text, post_element, post_index.
    Scrolls to load more posts if needed.
    """
    posts = []
    _dismiss_popups(page)

    # Scroll a bit to load posts
    for _ in range(3):
        page.mouse.wheel(0, 600)
        human_delay(1, 2)

    # Facebook posts typically live in divs with role="article"
    # or data-ad-preview="message" or similar
    post_selectors = [
        'div[role="article"]',
        'div[data-ad-comet-preview="message"]',
    ]

    post_elements = []
    for sel in post_selectors:
        found = page.locator(sel).all()
        if found:
            post_elements = found
            break

    for i, el in enumerate(post_elements[:max_posts]):
        try:
            text = el.inner_text(timeout=5000)
            # Clean up — take first ~500 chars as the meaningful text
            text = text.strip()[:500]
            if text:
                posts.append({
                    "text": text,
                    "post_index": i,
                    "element_selector": f'div[role="article"] >> nth={i}',
                })
        except Exception:
            continue

    log_action("browser", f"Read {len(posts)} posts from page")
    return posts


def comment_on_post(page: Page, post_index: int, comment_text: str) -> bool:
    """Post a comment on a specific post (identified by index on page).

    Returns True if the comment was posted successfully.
    """
    try:
        post = page.locator('div[role="article"]').nth(post_index)
        post.scroll_into_view_if_needed()
        human_delay(1, 2)

        # Click the comment button/area
        comment_triggers = [
            post.locator('[aria-label="Leave a comment"], [aria-label="Write a comment"]').first,
            post.locator('[aria-label="Comment"]').first,
            post.locator('div[role="button"]:has-text("Comment")').first,
        ]

        clicked = False
        for trigger in comment_triggers:
            try:
                if trigger.is_visible(timeout=3000):
                    trigger.click()
                    clicked = True
                    human_delay(1, 2)
                    break
            except Exception:
                continue

        if not clicked:
            log_action("browser", f"Could not find comment trigger for post {post_index}")
            return False

        # Type the comment into the comment box
        comment_box_selectors = [
            'div[role="textbox"][aria-label*="comment" i]',
            'div[role="textbox"][aria-label*="Comment" i]',
            'div[contenteditable="true"][aria-label*="comment" i]',
            'div[contenteditable="true"][aria-label*="Comment" i]',
            'div[role="textbox"]',
        ]

        typed = False
        for sel in comment_box_selectors:
            try:
                box = page.locator(sel).last
                if box.is_visible(timeout=3000):
                    box.click()
                    human_delay(0.5, 1)
                    box.fill(comment_text)
                    human_delay(1, 2)
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            log_action("browser", f"Could not find comment box for post {post_index}")
            return False

        # Submit — press Enter
        page.keyboard.press("Enter")
        human_delay(2, 4)

        log_action(
            "browser",
            f"Posted comment on post index {post_index}",
            comment_text=comment_text,
        )
        return True

    except Exception as e:
        log_action("browser", f"ERROR commenting on post {post_index}: {e}")
        return False


def check_comment_replies(page: Page, comment_text_snippet: str) -> list[dict]:
    """Check for replies to a comment we previously posted.

    Navigates through the page looking for our comment and any replies.
    Returns a list of reply dicts: {author, text}.
    """
    replies = []

    # Scroll to load content
    for _ in range(5):
        page.mouse.wheel(0, 500)
        human_delay(1, 2)

    # Look for our comment text on the page
    try:
        # Find elements containing our comment snippet
        our_comments = page.locator(f'text="{comment_text_snippet[:50]}"').all()
        if not our_comments:
            return replies

        for comment_el in our_comments:
            # Look for a "View replies" or reply section near our comment
            parent = comment_el.locator("xpath=ancestor::div[contains(@class, 'comment')]").first
            try:
                reply_btn = parent.locator('text=/View \\d+ repl/i').first
                if reply_btn.is_visible(timeout=2000):
                    reply_btn.click()
                    human_delay(2, 3)
            except Exception:
                pass

            # Collect reply texts
            reply_elements = parent.locator('ul li, div[role="article"]').all()
            for rel in reply_elements:
                try:
                    txt = rel.inner_text(timeout=3000)
                    if txt and comment_text_snippet[:30] not in txt:
                        replies.append({"text": txt.strip()[:300]})
                except Exception:
                    continue

    except Exception as e:
        log_action("browser", f"ERROR checking replies: {e}")

    return replies


def post_to_own_page(page: Page, content: str) -> bool:
    """Post content to the Vote Uncovered Facebook page.

    Navigates to the page and creates a new post.
    Returns True if successful.
    """
    if not navigate_to_page(page, FB_PAGE_ID):
        return False

    human_delay(2, 4)

    try:
        # Click on the "Create post" or "What's on your mind" area
        create_post_selectors = [
            '[aria-label="Create a post"]',
            'div[role="button"]:has-text("What\'s on your mind")',
            'div[role="button"]:has-text("Create a post")',
            'div[role="button"]:has-text("Write something")',
            'span:has-text("What\'s on your mind")',
        ]

        clicked = False
        for sel in create_post_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    clicked = True
                    human_delay(2, 3)
                    break
            except Exception:
                continue

        if not clicked:
            log_action("browser", "Could not find 'Create post' button on own page")
            return False

        # Wait for the post composition dialog
        human_delay(2, 3)

        # Type into the post composition area
        post_box_selectors = [
            'div[role="dialog"] div[role="textbox"]',
            'div[role="textbox"][aria-label*="on your mind"]',
            'div[role="textbox"][aria-label*="Create a post"]',
            'div[role="dialog"] div[contenteditable="true"]',
            'div[role="textbox"]',
        ]

        typed = False
        for sel in post_box_selectors:
            try:
                box = page.locator(sel).first
                if box.is_visible(timeout=5000):
                    box.click()
                    human_delay(0.5, 1)
                    # Type slowly for longer content
                    box.fill(content)
                    human_delay(1, 2)
                    typed = True
                    break
            except Exception:
                continue

        if not typed:
            log_action("browser", "Could not find post composition textbox")
            return False

        # Click the Post button
        post_btn_selectors = [
            'div[role="dialog"] div[role="button"][aria-label="Post"]',
            'div[role="dialog"] button:has-text("Post")',
            'div[role="button"][aria-label="Post"]',
            'button:has-text("Post")',
        ]

        for sel in post_btn_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    human_delay(3, 5)
                    log_action("browser", "Published post to own page", post_text=content[:200])
                    return True
            except Exception:
                continue

        log_action("browser", "Could not find Post submit button")
        return False

    except Exception as e:
        log_action("browser", f"ERROR posting to own page: {e}")
        return False


def cleanup(pw, browser, context):
    """Save state and close browser resources."""
    try:
        save_browser_state(context)
    except Exception as e:
        log_action("browser", f"Warning: could not save browser state: {e}")
    try:
        browser.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass


# ── CLI for testing individual operations ───────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Vote Uncovered browser automation")
    parser.add_argument("action", choices=["login", "read-posts", "comment", "post", "check-replies"],
                        help="Action to perform")
    parser.add_argument("--page", default=FB_PAGE_ID, help="Facebook page ID to interact with")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode (visible browser)")
    parser.add_argument("--text", default="", help="Text to post/comment")
    parser.add_argument("--post-index", type=int, default=0, help="Post index for commenting")

    args = parser.parse_args()

    pw, browser, context, page = create_browser_context(headless=not args.headed)

    try:
        if not login_to_facebook(page):
            print("Login failed. Check credentials in .env")
            return

        save_browser_state(context)

        if args.action == "login":
            print("Login successful!")

        elif args.action == "read-posts":
            navigate_to_page(page, args.page)
            posts = read_page_posts(page)
            for i, p in enumerate(posts):
                print(f"\n--- Post {i} ---")
                print(p["text"][:200])

        elif args.action == "comment":
            if not args.text:
                print("--text required for commenting")
                return
            navigate_to_page(page, args.page)
            human_delay(2, 3)
            success = comment_on_post(page, args.post_index, args.text)
            print(f"Comment {'posted' if success else 'failed'}")

        elif args.action == "post":
            if not args.text:
                print("--text required for posting")
                return
            success = post_to_own_page(page, args.text)
            print(f"Post {'published' if success else 'failed'}")

        elif args.action == "check-replies":
            navigate_to_page(page, args.page)
            replies = check_comment_replies(page, args.text or "vote")
            for r in replies:
                print(f"Reply: {r['text'][:150]}")

    finally:
        cleanup(pw, browser, context)


if __name__ == "__main__":
    main()
