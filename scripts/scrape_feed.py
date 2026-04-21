#!/usr/bin/env python3
"""
scrape_feed.py — Scroll Dominic's home feed and extract posts from approved pages.
Saves raw post data to data/feed_posts.json for AI review.
"""
import os, sys, time, json, random
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

def main(max_posts=30):
    # Load already-commented posts
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

    def nuke():
        page.evaluate('() => document.querySelectorAll("div[role=dialog]").forEach(e=>e.remove())')

    page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
    time.sleep(10)

    posts_found = []
    seen_keys = set()
    scroll_count = 0
    max_scrolls = 30

    while len(posts_found) < max_posts and scroll_count < max_scrolls:
        nuke()

        posts_data = page.evaluate('''() => {
            const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
            return Array.from(buttons).map((btn, idx) => {
                let container = btn;
                for (let i = 0; i < 15; i++) {
                    container = container.parentElement;
                    if (!container) break;
                }
                const textEls = container ? container.querySelectorAll('div[dir="auto"]') : [];
                const texts = Array.from(textEls).map(t => t.textContent).filter(t => t.length > 20);
                const links = container ? container.querySelectorAll('a[role="link"]') : [];
                const pageNames = Array.from(links).map(l => l.textContent).filter(t => t.length > 3 && t.length < 50);
                // Try to get post URL
                const postLinks = container ? container.querySelectorAll('a[href*="pfbid"], a[href*="/posts/"], a[href*="/reel/"]') : [];
                const postUrl = postLinks.length > 0 ? postLinks[0].href : '';
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
            print(f'Found: [{page_name}] {post_text[:80]}...')

        page.mouse.wheel(0, random.randint(400, 700))
        time.sleep(random.randint(3, 5))
        scroll_count += 1

    # Save state
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))

    # Save posts
    output_path = PROJECT_ROOT / 'data' / 'feed_posts.json'
    output_path.write_text(json.dumps(posts_found, indent=2))
    print(f'\nSaved {len(posts_found)} posts to {output_path}')

    browser.close()
    pw.stop()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=30, help='Max posts to scrape')
    args = parser.parse_args()
    main(max_posts=args.max)
