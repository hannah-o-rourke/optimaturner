#!/usr/bin/env python3
"""
live_comment.py — Single-pass interactive commenting.

Scrolls the home feed. For each post from an approved page:
1. Prints POST_FOUND JSON to stdout
2. Waits for a line on stdin:
   - "COMMENT: <text>" → posts the comment
   - "SKIP" → moves on
3. If commenting, clicks "Leave a comment", types, submits

This keeps the browser on the exact same scroll position, so posts
don't disappear.

Usage: python3 live_comment.py
  (interact via stdin/stdout)
"""
import os, sys, time, csv, json, random
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

APPROVED_PAGES = [
    "Bristol Post", "Coventry Live", "Grimsby Live", "Leicester Mercury",
    "Nottingham Post", "Stoke Sentinel", "Wales Online",
    "Basingstoke Gazette", "Derbyshire Times", "Falkirk Herald",
    "bristol.live", "livecoventry", "grimsbylive", "leicestershirelive",
    "nottinghamshirelive", "stokeontrentlive", "WalesOnline",
    "basingstokegazette", "derbyshiretimes", "falkirkherald",
    "Bristol.Live", "Coventry Live", "GrimsbyLive", "Leicestershire Live",
    "Nottinghamshire Live", "Stoke-on-Trent Live",
]

WELSH_PAGES = ["Wales Online", "WalesOnline"]
SCOTTISH_PAGES = ["Falkirk Herald", "falkirkherald"]


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


def nuke(page):
    page.evaluate('() => document.querySelectorAll("div[role=dialog]").forEach(e=>e.remove())')


def main(max_comments=8):
    commented_file = PROJECT_ROOT / 'data' / 'commented.json'
    commented = set()
    if commented_file.exists():
        commented = set(json.loads(commented_file.read_text()))

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

    page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
    time.sleep(10)

    seen_keys = set()
    comments_posted = 0

    for scroll_count in range(30):
        if comments_posted >= max_comments:
            break

        nuke(page)
        posts_data = page.evaluate('''() => {
            const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
            return Array.from(buttons).map((btn, idx) => {
                let container = btn;
                for (let i = 0; i < 15; i++) { container = container.parentElement; if (!container) break; }
                const textEls = container ? container.querySelectorAll('div[dir="auto"]') : [];
                const texts = Array.from(textEls).map(t => t.textContent).filter(t => t.length > 20);
                const links = container ? container.querySelectorAll('a[role="link"]') : [];
                const pageNames = Array.from(links).map(l => l.textContent).filter(t => t.length > 3 && t.length < 50);
                const postLinks = container ? container.querySelectorAll('a[href*="pfbid"], a[href*="/posts/"], a[href*="/reel/"]') : [];
                // Also check timestamp links and any other links that might contain post URLs
                const allLinks = container ? container.querySelectorAll('a[href]') : [];
                let postUrl = '';
                if (postLinks.length > 0) {
                    postUrl = postLinks[0].href;
                } else {
                    for (const link of allLinks) {
                        const h = link.href || '';
                        if (h.includes('pfbid') || h.includes('/posts/') || h.includes('/reel/') || 
                            (h.includes('facebook.com/') && h.includes('/photos/')) ||
                            (h.includes('facebook.com/') && h.includes('story_fbid'))) {
                            postUrl = h;
                            break;
                        }
                    }
                }
                const rect = btn.getBoundingClientRect();
                return {
                    idx: idx,
                    texts: texts.slice(0, 5).map(t => t.substring(0, 500)),
                    pageNames: pageNames.slice(0, 5),
                    postUrl: postUrl,
                    y: rect.y,
                    visible: rect.y > 0 && rect.y < 900
                };
            });
        }''')

        for post in posts_data:
            if not post['visible'] or comments_posted >= max_comments:
                continue

            post_text = ' '.join(post['texts'])
            page_name = ''
            for name in post['pageNames']:
                if any(ap.lower() in name.lower() for ap in APPROVED_PAGES):
                    page_name = name
                    break
            if not page_name:
                continue

            post_key = post_text[:100]
            if post_key in seen_keys or post_key in commented:
                continue
            seen_keys.add(post_key)

            # Determine election type for context
            election_type = "local council elections"
            if any(w in page_name for w in WELSH_PAGES):
                election_type = "the Senedd election"
            elif any(s in page_name for s in SCOTTISH_PAGES):
                election_type = "the Scottish Parliament election"

            # Output post for AI to judge
            post_info = json.dumps({
                "page_name": page_name,
                "post_text": post_text[:500],
                "election_type": election_type,
                "button_idx": post['idx'],
                "post_url": post.get('postUrl', ''),
            })
            print(f"POST_FOUND:{post_info}", flush=True)

            # Wait for decision on stdin
            try:
                line = input()
            except EOFError:
                break

            line = line.strip()
            if line.startswith("COMMENT:"):
                comment_text = line[8:].strip()

                # Find the correct post by matching text content, then click ITS comment button
                # This avoids button index drift when Facebook loads new content
                target_snippet = post_text[:60].replace("'", "\\'")
                clicked = page.evaluate(f'''(snippet) => {{
                    const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
                    for (const btn of buttons) {{
                        let container = btn;
                        for (let i = 0; i < 15; i++) {{ container = container.parentElement; if (!container) break; }}
                        if (container && container.innerText.includes(snippet)) {{
                            btn.scrollIntoView({{block: "center"}});
                            return true;
                        }}
                    }}
                    return false;
                }}''', target_snippet)
                
                if not clicked:
                    print("RESULT:POST_NOT_FOUND", flush=True)
                    continue
                
                time.sleep(2)
                
                # Now find and click the button that's near this text
                btn_clicked = page.evaluate(f'''(snippet) => {{
                    const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
                    for (const btn of buttons) {{
                        let container = btn;
                        for (let i = 0; i < 15; i++) {{ container = container.parentElement; if (!container) break; }}
                        if (container && container.innerText.includes(snippet)) {{
                            const r = btn.getBoundingClientRect();
                            ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t => {{
                                btn.dispatchEvent(new MouseEvent(t, {{bubbles:true,cancelable:true,clientX:r.x+5,clientY:r.y+5}}));
                            }});
                            return true;
                        }}
                    }}
                    return false;
                }}''', target_snippet)
                
                if not btn_clicked:
                    print("RESULT:CLICK_FAILED", flush=True)
                    continue

                time.sleep(6)

                tb = page.locator('[contenteditable="true"][role="textbox"][aria-label*="Comment"]').first
                if not tb.is_visible(timeout=5000):
                    print("RESULT:NO_COMMENT_BOX", flush=True)
                    page.keyboard.press('Escape')
                    time.sleep(2)
                    continue

                tb.click(force=True)
                time.sleep(1)
                tb.press_sequentially(comment_text, delay=random.randint(20, 40))
                time.sleep(2)
                dispatch_click(page, '[aria-label="Post comment"]')
                time.sleep(random.randint(4, 8))

                # Try to grab post URL from the modal/page after clicking
                post_url = post.get('postUrl', '')
                if not post_url:
                    post_url = page.evaluate('''() => {
                        const links = document.querySelectorAll('a[href*="pfbid"], a[href*="/posts/"], a[href*="comment_id"]');
                        for (const l of links) {
                            if (l.href && (l.href.includes('pfbid') || l.href.includes('/posts/'))) return l.href;
                        }
                        // Try the URL bar if we navigated
                        if (window.location.href.includes('pfbid') || window.location.href.includes('/posts/')) return window.location.href;
                        return '';
                    }''') or 'home_feed'
                log_comment(page_name, post_url, comment_text)
                commented.add(post_key)
                comments_posted += 1
                print(f"RESULT:POSTED:{comments_posted}", flush=True)

                page.keyboard.press('Escape')
                time.sleep(random.randint(3, 6))
                nuke(page)

            elif line == "SKIP":
                continue
            elif line == "DONE":
                break

        page.mouse.wheel(0, random.randint(400, 700))
        time.sleep(random.randint(3, 5))

    # Save state
    commented_file.write_text(json.dumps(list(commented)))
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
    print(f"SESSION_DONE:posted={comments_posted}", flush=True)
    browser.close()
    pw.stop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=8)
    args = parser.parse_args()
    main(max_comments=args.max)
