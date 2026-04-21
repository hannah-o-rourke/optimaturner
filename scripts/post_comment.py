#!/usr/bin/env python3
"""
post_comment.py — Post a single comment on a Facebook post via Dominic's home feed.
Usage: python3 post_comment.py --post-url <url> --comment <text>
"""
import os, sys, time, csv, json, random
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def dispatch_click(page, sel):
    return page.evaluate('''(sel) => {
        const btn = document.querySelector(sel);
        if (btn) {
            const r = btn.getBoundingClientRect();
            ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t => {
                btn.dispatchEvent(new MouseEvent(t, {bubbles:true,cancelable:true,clientX:r.x+5,clientY:r.y+5}));
            });
            return true;
        }
        return false;
    }''', sel)


def log_comment(page_name, post_url, comment_text):
    csv_path = PROJECT_ROOT / "logs" / "comments.csv"
    csv_path.parent.mkdir(exist_ok=True)
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0
    with open(csv_path, 'a', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        if not file_exists:
            w.writerow(["timestamp", "page_name", "page_url", "post_url", "comment_text", "comment_url"])
        w.writerow([datetime.now(timezone.utc).isoformat(), page_name, "https://www.facebook.com/", post_url, comment_text, ''])


def main(post_url, comment_text, page_name="Unknown"):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 900},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        locale='en-GB',
        storage_state=str(PROJECT_ROOT / 'data' / 'dominic_state.json')
    )
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

    def nuke():
        page.evaluate('() => document.querySelectorAll("div[role=dialog]").forEach(e=>e.remove())')

    # Go to home feed first
    page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
    time.sleep(8)

    # Now navigate to the specific post
    page.goto(post_url, wait_until='domcontentloaded')
    time.sleep(8)
    nuke()

    # Try to find comment box directly on the post page
    # First try clicking "Leave a comment" if present
    try:
        leave_btn = page.locator('[aria-label="Leave a comment"]').first
        if leave_btn.is_visible(timeout=3000):
            leave_btn.click()
            time.sleep(4)
    except:
        pass

    nuke()

    # Find the comment textbox
    tb = page.locator('[contenteditable="true"][role="textbox"][aria-label*="comment" i]').first
    if not tb.is_visible(timeout=8000):
        # Try scrolling down to find it
        page.mouse.wheel(0, 500)
        time.sleep(3)
        nuke()
        tb = page.locator('[contenteditable="true"][role="textbox"][aria-label*="comment" i]').first
        if not tb.is_visible(timeout=5000):
            print("ERROR: Could not find comment box")
            ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
            browser.close()
            pw.stop()
            return False

    tb.click(force=True)
    time.sleep(1)
    tb.press_sequentially(comment_text, delay=random.randint(20, 40))
    time.sleep(2)

    if not dispatch_click(page, '[aria-label="Post comment"]'):
        # Try alternate selector
        dispatch_click(page, '[aria-label="Comment"]')
    time.sleep(random.randint(4, 8))

    log_comment(page_name, post_url, comment_text)

    # Update commented list
    commented_file = PROJECT_ROOT / 'data' / 'commented.json'
    commented = set()
    if commented_file.exists():
        commented = set(json.loads(commented_file.read_text()))
    commented.add(post_url[:200])
    commented_file.write_text(json.dumps(list(commented)))

    # Save state
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))

    print(f"✅ Comment posted on {page_name}: {comment_text[:80]}...")
    browser.close()
    pw.stop()
    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--post-url', required=True)
    parser.add_argument('--comment', required=True)
    parser.add_argument('--page-name', default='Unknown')
    args = parser.parse_args()
    main(args.post_url, args.comment, args.page_name)
