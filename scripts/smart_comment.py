#!/usr/bin/env python3
"""
smart_comment.py — Two-phase commenting:
  Phase 1 (--scrape): Scroll home feed, save posts to data/feed_posts.json
  Phase 2 (--comment): Read data/comments_to_post.json and post them via home feed

The AI reads feed_posts.json between phases, writes comments_to_post.json,
then calls phase 2.

Usage:
  python3 smart_comment.py --scrape --max 30
  # AI reviews feed_posts.json, writes comments_to_post.json
  python3 smart_comment.py --comment
"""
import os, sys, time, csv, json, random, re
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


def make_browser():
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
    return pw, browser, ctx, page


def nuke(page):
    page.evaluate('() => document.querySelectorAll("div[role=dialog]").forEach(e=>e.remove())')


def scrape(max_posts=30):
    """Phase 1: Scrape home feed, save posts to JSON."""
    commented_file = PROJECT_ROOT / 'data' / 'commented.json'
    commented = set()
    if commented_file.exists():
        commented = set(json.loads(commented_file.read_text()))

    pw, browser, ctx, page = make_browser()
    page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
    time.sleep(10)

    posts_found = []
    seen_keys = set()
    scroll_count = 0

    while len(posts_found) < max_posts and scroll_count < 30:
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
                const postUrl = postLinks.length > 0 ? postLinks[0].href : '';
                
                // Also grab any timestamp/time links as they often contain post URLs
                const timeLinks = container ? container.querySelectorAll('a[href*="facebook.com"]') : [];
                const allUrls = Array.from(timeLinks).map(l => l.href).filter(h => h.includes('pfbid') || h.includes('/posts/') || h.includes('/reel/'));
                
                const rect = btn.getBoundingClientRect();
                return {
                    idx: idx,
                    texts: texts.slice(0, 5).map(t => t.substring(0, 500)),
                    pageNames: pageNames.slice(0, 5),
                    postUrl: postUrl || (allUrls.length > 0 ? allUrls[0] : ''),
                    y: rect.y,
                    visible: rect.y > 0 && rect.y < 900
                };
            });
        }''')

        for post in posts_data:
            if not post['visible'] or len(posts_found) >= max_posts:
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
            posts_found.append({
                'page_name': page_name,
                'post_text': post_text[:1000],
                'post_url': post['postUrl'],
                'button_idx': post['idx'],
                'scraped_at': datetime.now(timezone.utc).isoformat(),
            })
            print(f'Found: [{page_name}] {post_text[:100]}...')

        page.mouse.wheel(0, random.randint(400, 700))
        time.sleep(random.randint(3, 5))
        scroll_count += 1

    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
    output_path = PROJECT_ROOT / 'data' / 'feed_posts.json'
    output_path.write_text(json.dumps(posts_found, indent=2))
    print(f'\nSaved {len(posts_found)} posts to {output_path}')
    browser.close()
    pw.stop()


def post_comments():
    """Phase 2: Read AI-written comments and post them via home feed."""
    comments_file = PROJECT_ROOT / 'data' / 'comments_to_post.json'
    if not comments_file.exists():
        print("No comments_to_post.json found — nothing to post")
        return

    comments = json.loads(comments_file.read_text())
    if not comments:
        print("No comments to post")
        return

    commented_file = PROJECT_ROOT / 'data' / 'commented.json'
    commented = set()
    if commented_file.exists():
        commented = set(json.loads(commented_file.read_text()))

    pw, browser, ctx, page = make_browser()
    page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
    time.sleep(10)

    posted = 0
    for item in comments:
        comment_text = item['comment']
        page_name = item.get('page_name', 'Unknown')
        post_text_snippet = item.get('post_text', '')[:100]

        print(f'\n{"="*60}')
        print(f'Looking for: [{page_name}] {post_text_snippet}...')
        print(f'Comment: {comment_text}')

        # Scroll through feed to find this post
        found = False
        for scroll in range(25):
            nuke(page)
            posts_data = page.evaluate('''() => {
                const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
                return Array.from(buttons).map((btn, idx) => {
                    let container = btn;
                    for (let i = 0; i < 15; i++) { container = container.parentElement; if (!container) break; }
                    const texts = container ? Array.from(container.querySelectorAll('div[dir="auto"]')).map(t => t.textContent).filter(t => t.length > 20) : [];
                    const links = container ? Array.from(container.querySelectorAll('a[role="link"]')).map(l => l.textContent).filter(t => t.length > 3) : [];
                    const postLinks = container ? Array.from(container.querySelectorAll('a[href*="pfbid"], a[href*="/posts/"]')).map(l => l.href) : [];
                    const rect = btn.getBoundingClientRect();
                    return { idx, texts: texts.slice(0,3).map(t=>t.substring(0,300)), pageNames: links.slice(0,5), postUrl: postLinks[0]||'', y: rect.y, visible: rect.y > 0 && rect.y < 900 };
                });
            }''')

            for post in posts_data:
                if not post['visible']:
                    continue
                combined = ' '.join(post['texts'])
                # Match by post text similarity
                if post_text_snippet[:50] and post_text_snippet[:50] in combined:
                    print(f'MATCH at idx {post["idx"]}')
                    # Scroll into view and click "Leave a comment"
                    page.evaluate(f'''() => {{
                        const btns = document.querySelectorAll('[aria-label="Leave a comment"]');
                        if (btns[{post["idx"]}]) btns[{post["idx"]}].scrollIntoView({{block:"center"}});
                    }}''')
                    time.sleep(2)
                    btn = page.locator('[aria-label="Leave a comment"]').nth(post['idx'])
                    try:
                        btn.click(timeout=10000)
                    except:
                        print('Click failed')
                        continue
                    time.sleep(6)

                    tb = page.locator('[contenteditable="true"][role="textbox"][aria-label*="Comment"]').first
                    if not tb.is_visible(timeout=5000):
                        print('No comment box')
                        page.keyboard.press('Escape')
                        time.sleep(2)
                        continue

                    tb.click(force=True)
                    time.sleep(1)
                    tb.press_sequentially(comment_text, delay=random.randint(20, 40))
                    time.sleep(2)
                    dispatch_click(page, '[aria-label="Post comment"]')
                    time.sleep(random.randint(4, 8))

                    log_comment(page_name, post['postUrl'] or 'home_feed', comment_text)
                    commented.add(post_text_snippet)
                    posted += 1
                    print(f'✅ POSTED ({posted}/{len(comments)})')

                    page.keyboard.press('Escape')
                    time.sleep(random.randint(3, 6))
                    nuke(page)
                    found = True
                    break

            if found:
                break
            page.mouse.wheel(0, random.randint(400, 700))
            time.sleep(random.randint(2, 4))

        if not found:
            print(f'⚠️ Could not find post on feed — skipped')

    commented_file.write_text(json.dumps(list(commented)))
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
    print(f'\n{"="*60}')
    print(f'Done! Posted {posted}/{len(comments)} comments.')
    browser.close()
    pw.stop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--scrape', action='store_true', help='Phase 1: scrape feed')
    parser.add_argument('--comment', action='store_true', help='Phase 2: post comments')
    parser.add_argument('--max', type=int, default=30, help='Max posts to scrape')
    args = parser.parse_args()
    if args.scrape:
        scrape(max_posts=args.max)
    elif args.comment:
        post_comments()
    else:
        print("Specify --scrape or --comment")
