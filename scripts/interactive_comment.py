#!/usr/bin/env python3
"""
interactive_comment.py — Single-session scrape + comment.

Phase 1: Scroll feed, collect posts from approved pages, save to feed_posts.json
Phase 2: Read comments_to_post.json (written by AI between phases)  
Phase 3: Scroll feed AGAIN in same session and post comments

The key difference from smart_comment.py: phases 1-3 happen in ONE browser session,
so the feed doesn't reshuffle between scrape and post.

Usage:
  python3 interactive_comment.py --phase scrape   # scrape only, keep browser state
  python3 interactive_comment.py --phase post      # post only (reads comments_to_post.json)
  python3 interactive_comment.py --phase all        # scrape, wait for comments file, then post
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


def get_feed_posts(page):
    """Extract visible posts with 'Leave a comment' buttons."""
    return page.evaluate('''() => {
        const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
        return Array.from(buttons).map((btn, idx) => {
            let container = btn;
            for (let i = 0; i < 15; i++) { container = container.parentElement; if (!container) break; }
            const textEls = container ? container.querySelectorAll('div[dir="auto"]') : [];
            const texts = Array.from(textEls).map(t => t.textContent).filter(t => t.length > 20);
            const links = container ? container.querySelectorAll('a[role="link"]') : [];
            const pageNames = Array.from(links).map(l => l.textContent).filter(t => t.length > 3 && t.length < 50);
            const postLinks = container ? container.querySelectorAll('a[href*="pfbid"], a[href*="/posts/"], a[href*="/reel/"]') : [];
            const timeLinks = container ? container.querySelectorAll('a[href*="facebook.com"]') : [];
            const allUrls = Array.from(timeLinks).map(l => l.href).filter(h => h.includes('pfbid') || h.includes('/posts/') || h.includes('/reel/'));
            const rect = btn.getBoundingClientRect();
            return {
                idx: idx,
                texts: texts.slice(0, 5).map(t => t.substring(0, 500)),
                pageNames: pageNames.slice(0, 5),
                postUrl: (postLinks.length > 0 ? postLinks[0].href : '') || (allUrls.length > 0 ? allUrls[0] : ''),
                y: rect.y,
                visible: rect.y > 0 && rect.y < 900
            };
        });
    }''')


def try_comment_on_post(page, post_idx, comment_text):
    """Try to comment on a post at the given button index. Returns True if successful."""
    # Scroll into view
    page.evaluate(f'''() => {{
        const btns = document.querySelectorAll('[aria-label="Leave a comment"]');
        if (btns[{post_idx}]) btns[{post_idx}].scrollIntoView({{block:"center"}});
    }}''')
    time.sleep(2)

    btn = page.locator('[aria-label="Leave a comment"]').nth(post_idx)
    try:
        btn.click(timeout=10000)
    except:
        print('  Click failed')
        return False

    time.sleep(6)

    tb = page.locator('[contenteditable="true"][role="textbox"][aria-label*="Comment"]').first
    if not tb.is_visible(timeout=5000):
        print('  No comment box found')
        page.keyboard.press('Escape')
        time.sleep(2)
        return False

    tb.click(force=True)
    time.sleep(1)
    tb.press_sequentially(comment_text, delay=random.randint(20, 40))
    time.sleep(2)
    dispatch_click(page, '[aria-label="Post comment"]')
    time.sleep(random.randint(4, 8))

    page.keyboard.press('Escape')
    time.sleep(random.randint(3, 6))
    nuke(page)
    return True


def main(phase='all'):
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

    if phase in ('scrape', 'all'):
        # PHASE 1: Scrape
        posts_found = []
        seen_keys = set()
        for scroll_count in range(30):
            nuke(page)
            posts_data = get_feed_posts(page)
            for post in posts_data:
                if not post['visible']:
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

        output_path = PROJECT_ROOT / 'data' / 'feed_posts.json'
        output_path.write_text(json.dumps(posts_found, indent=2))
        print(f'\n=== Scrape done: {len(posts_found)} posts saved ===')
        print('SCRAPE_COMPLETE')
        sys.stdout.flush()

    if phase == 'scrape':
        ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
        browser.close()
        pw.stop()
        return

    if phase == 'all':
        # Wait for AI to write comments_to_post.json
        comments_file = PROJECT_ROOT / 'data' / 'comments_to_post.json'
        # Record scrape completion time so we only accept files written AFTER scrape
        scrape_done_time = time.time()
        print('Waiting for NEW comments_to_post.json (written after scrape)...')
        sys.stdout.flush()
        waited = 0
        while waited < 300:  # 5 min max wait
            if comments_file.exists():
                mtime = comments_file.stat().st_mtime
                if mtime > scrape_done_time:
                    time.sleep(2)  # Let file finish writing
                    print('Found new comments file!')
                    break
            time.sleep(5)
            waited += 5
        else:
            print('No new comments file after 5 minutes — exiting')
            ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
            browser.close()
            pw.stop()
            return

    # PHASE 2: Post comments
    comments_file = PROJECT_ROOT / 'data' / 'comments_to_post.json'
    if not comments_file.exists():
        print('No comments_to_post.json — nothing to post')
        ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
        browser.close()
        pw.stop()
        return

    comments = json.loads(comments_file.read_text())
    if not comments:
        print('Empty comments list — nothing to post')
        ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
        browser.close()
        pw.stop()
        return

    # Scroll back to top of feed
    page.evaluate('window.scrollTo(0, 0)')
    time.sleep(5)

    posted = 0
    for item in comments:
        comment_text = item['comment']
        page_name = item.get('page_name', 'Unknown')
        target_text = item.get('post_text', '')[:80]

        print(f'\n=== Posting on [{page_name}]: {target_text}... ===')
        print(f'Comment: {comment_text}')

        found = False
        for scroll in range(30):
            nuke(page)
            posts_data = get_feed_posts(page)
            for post in posts_data:
                if not post['visible']:
                    continue
                combined = ' '.join(post['texts'])
                # Match by first 50 chars of post text
                if target_text[:50] and target_text[:50] in combined:
                    print(f'  MATCH at button idx {post["idx"]}')
                    if try_comment_on_post(page, post['idx'], comment_text):
                        post_url = post.get('postUrl', '') or 'home_feed'
                        log_comment(page_name, post_url, comment_text)
                        commented.add(target_text[:100])
                        posted += 1
                        print(f'  ✅ POSTED ({posted}/{len(comments)})')
                    found = True
                    break
            if found:
                break
            page.mouse.wheel(0, random.randint(400, 700))
            time.sleep(random.randint(2, 4))

        if not found:
            print(f'  ⚠️ Could not find post — skipped')

    commented_file.write_text(json.dumps(list(commented)))
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
    print(f'\n{"="*60}')
    print(f'Done! Posted {posted}/{len(comments)} comments.')
    browser.close()
    pw.stop()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['scrape', 'post', 'all'], default='all')
    args = parser.parse_args()
    main(phase=args.phase)
