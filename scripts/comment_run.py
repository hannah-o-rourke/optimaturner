#!/usr/bin/env python3
"""
comment_run.py — Scroll Dominic's home feed, find posts from approved pages,
and post contextual comments about upcoming elections.
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

WELSH_PAGES = ["Wales Online", "WalesOnline"]
SCOTTISH_PAGES = ["Falkirk Herald", "falkirkherald"]

LOCAL_ISSUE_KEYWORDS = [
    "council", "councillor", "road", "pothole", "bin", "rubbish", "waste",
    "housing", "rent", "tenant", "planning", "development", "park",
    "school", "transport", "bus", "traffic", "parking", "nhs", "hospital",
    "police", "crime", "antisocial", "anti-social", "flooding", "flood",
    "library", "leisure", "playground", "pavement", "footpath", "cycling",
    "homeless", "homelessness", "eviction", "traveller", "regeneration",
    "budget", "council tax", "funding", "closure", "closing down",
    "community", "neighbourhood", "local", "residents", "petition",
    "green space", "environment", "pollution", "air quality",
]

SKIP_TOPICS = [
    "westminster", "parliament", "prime minister", "starmer", "sunak",
    "general election", "national", "celebrity", "premier league",
    "champions league", "world cup", "love island", "strictly",
    "weather forecast", "recipe", "quiz",
]

def is_relevant(text):
    lower = text.lower()
    if any(skip in lower for skip in SKIP_TOPICS):
        return False
    return any(kw in lower for kw in LOCAL_ISSUE_KEYWORDS)

def get_election_type(page_name):
    if any(w in page_name for w in WELSH_PAGES):
        return "the Senedd election"
    if any(s in page_name for s in SCOTTISH_PAGES):
        return "the Scottish Parliament election"
    return "local council elections"

def craft_comment(post_text, page_name):
    """Generate a natural, contextual comment based on the post content."""
    election = get_election_type(page_name)
    lower = post_text.lower()
    
    # Match the comment to the topic
    if any(w in lower for w in ["road", "pothole", "traffic", "transport", "bus", "parking", "cycling"]):
        templates = [
            f"Roads and transport are decided by your local council. {election.capitalize()} are on May 7th — if this matters to you, that's your chance to have a say. whocanivotefor.co.uk",
            f"This is the kind of thing your local councillors are responsible for. {election.capitalize()} are coming up on May 7th — worth checking who's standing in your area at whocanivotefor.co.uk",
            f"Transport issues like this are exactly what gets decided at the local level. With {election} on May 7th, you get to choose who sorts this out. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["housing", "rent", "tenant", "eviction", "homeless", "homelessness", "traveller"]):
        templates = [
            f"Housing is one of the biggest issues local councils deal with. {election.capitalize()} are on May 7th — your vote shapes how this is handled. whocanivotefor.co.uk",
            f"These kinds of housing decisions are made at the local level. With {election} on May 7th, it's worth making your voice heard. whocanivotefor.co.uk",
            f"Local housing policy matters and it's decided by the people you elect. {election.capitalize()} are on May 7th — check who's standing at whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["bin", "rubbish", "waste", "recycling", "litter"]):
        templates = [
            f"Bins and waste collection — classic local council territory! {election.capitalize()} are on May 7th, and these are exactly the issues your councillors handle. whocanivotefor.co.uk",
            f"If this winds you up, it's worth knowing your local council is responsible for it. {election.capitalize()} are on May 7th — have your say at whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["police", "crime", "antisocial", "anti-social"]):
        templates = [
            f"Community safety is something local representatives can actually influence. {election.capitalize()} are on May 7th — a few minutes of your time could help shape what happens next. whocanivotefor.co.uk",
            f"Issues like this are why local elections matter. {election.capitalize()} are on May 7th — check who's standing in your area and what they'd do about it. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["council", "councillor", "council tax", "budget", "funding"]):
        templates = [
            f"This is exactly what {election} on May 7th are about. Your vote decides who makes these calls. Worth a look at whocanivotefor.co.uk to see who's standing.",
            f"Council decisions affect everyone — and on May 7th you get to decide who's making them. Check who's standing in your area: whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["park", "green space", "playground", "leisure", "library", "community"]):
        templates = [
            f"Local spaces like this are managed by your council. {election.capitalize()} are on May 7th — if you care about your community, it's worth having your say. whocanivotefor.co.uk",
            f"These are the things your local councillors look after. With {election} on May 7th, you get a say in who does it. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["school", "education"]):
        templates = [
            f"Education and local schools are shaped by decisions at the local level. {election.capitalize()} are on May 7th — your vote matters more than you think. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["planning", "development", "regeneration", "building"]):
        templates = [
            f"Planning decisions like this are made by your local council. {election.capitalize()} are on May 7th — it's your chance to pick who makes these choices. whocanivotefor.co.uk",
            f"If you've got opinions on local development, {election} on May 7th are your chance to be heard. See who's standing: whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ["flood", "environment", "pollution", "air quality"]):
        templates = [
            f"Environmental issues like this often come down to local decision-making. {election.capitalize()} are on May 7th — have your say on who handles it. whocanivotefor.co.uk",
        ]
    else:
        templates = [
            f"Local issues like this are decided by the people you elect. {election.capitalize()} are on May 7th — takes a couple of minutes to check who's standing in your area at whocanivotefor.co.uk",
            f"This is the kind of thing that gets sorted (or not!) at the local level. {election.capitalize()} are coming up on May 7th. whocanivotefor.co.uk",
        ]
    
    return random.choice(templates)

def log_comment(page_name, page_url, post_url, comment_text):
    csv_path = PROJECT_ROOT / "logs" / "comments.csv"
    csv_path.parent.mkdir(exist_ok=True)
    with open(csv_path, 'a', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow([datetime.now(timezone.utc).isoformat(), page_name, page_url, post_url, comment_text, ''])

def main(max_comments=5, dry_run=False):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    ctx = browser.new_context(
        viewport={'width':1280,'height':900},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        locale='en-GB',
        storage_state=str(PROJECT_ROOT / 'data' / 'dominic_state.json')
    )
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    
    def nuke():
        page.evaluate('() => document.querySelectorAll("div[role=dialog]").forEach(e=>e.remove())')
    
    def dispatch_click(sel):
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
    
    # Load commented posts to avoid duplicates
    commented_file = PROJECT_ROOT / 'data' / 'commented.json'
    commented_file.parent.mkdir(exist_ok=True)
    commented = set()
    if commented_file.exists():
        commented = set(json.loads(commented_file.read_text()))
    
    page.goto('https://www.facebook.com/', wait_until='domcontentloaded')
    time.sleep(10)
    
    comments_posted = 0
    scroll_count = 0
    max_scrolls = 30
    
    while comments_posted < max_comments and scroll_count < max_scrolls:
        nuke()
        
        # Get all "Leave a comment" buttons with their post context
        posts_data = page.evaluate('''() => {
            const buttons = document.querySelectorAll('[aria-label="Leave a comment"]');
            return Array.from(buttons).map((btn, idx) => {
                // Walk up to find the post container and its text
                let container = btn;
                for (let i = 0; i < 15; i++) {
                    container = container.parentElement;
                    if (!container) break;
                }
                const textEls = container ? container.querySelectorAll('div[dir="auto"]') : [];
                const texts = Array.from(textEls).map(t => t.textContent).filter(t => t.length > 20);
                
                // Find page name from links
                const links = container ? container.querySelectorAll('a[role="link"]') : [];
                const pageNames = Array.from(links).map(l => l.textContent).filter(t => t.length > 3 && t.length < 50);
                
                const rect = btn.getBoundingClientRect();
                return {
                    idx: idx,
                    texts: texts.slice(0, 3).map(t => t.substring(0, 200)),
                    pageNames: pageNames.slice(0, 5),
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
            
            # Check if post is relevant
            if not is_relevant(post_text):
                print(f'SKIP (not relevant): {page_name}: {post_text[:80]}...')
                continue
            
            # Check if already commented
            post_key = post_text[:100]
            if post_key in commented:
                print(f'SKIP (already commented): {page_name}: {post_text[:80]}...')
                continue
            
            comment = craft_comment(post_text, page_name)
            print(f'\n{"="*60}')
            print(f'PAGE: {page_name}')
            print(f'POST: {post_text[:120]}...')
            print(f'COMMENT: {comment}')
            
            if dry_run:
                print('DRY RUN — not posting')
                comments_posted += 1
                continue
            
            # Scroll the button into view and click
            page.evaluate(f'''() => {{
                const btns = document.querySelectorAll('[aria-label="Leave a comment"]');
                if (btns[{post['idx']}]) btns[{post['idx']}].scrollIntoView({{block:"center"}});
            }}''')
            time.sleep(2)
            
            # Click to open modal
            btn = page.locator('[aria-label="Leave a comment"]').nth(post['idx'])
            try:
                btn.click(timeout=10000)
            except:
                print('Click failed, skipping')
                continue
            
            time.sleep(6)
            
            # Find comment box in modal
            tb = page.locator('[contenteditable="true"][role="textbox"][aria-label*="Comment"]').first
            if not tb.is_visible(timeout=5000):
                print('No comment box found, closing modal')
                page.keyboard.press('Escape')
                time.sleep(2)
                continue
            
            tb.click(force=True)
            time.sleep(1)
            tb.press_sequentially(comment, delay=random.randint(20, 40))
            time.sleep(2)
            
            dispatch_click('[aria-label="Post comment"]')
            time.sleep(random.randint(4, 8))
            
            # Get the post URL from the modal
            post_url = page.evaluate('''() => {
                const links = document.querySelectorAll('a[href*="pfbid"], a[href*="/posts/"]');
                for (const l of links) if (l.href) return l.href;
                return window.location.href;
            }''')
            
            log_comment(page_name, f'https://www.facebook.com/', post_url, comment)
            commented.add(post_key)
            comments_posted += 1
            print(f'✅ POSTED! ({comments_posted}/{max_comments})')
            
            # Close modal
            page.keyboard.press('Escape')
            time.sleep(random.randint(3, 6))
            nuke()
        
        # Scroll for more posts
        page.mouse.wheel(0, random.randint(400, 700))
        time.sleep(random.randint(3, 5))
        scroll_count += 1
    
    # Save commented posts
    commented_file.write_text(json.dumps(list(commented)))
    
    # Save browser state
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'dominic_state.json'))
    
    print(f'\n{"="*60}')
    print(f'Done! Posted {comments_posted} comments.')
    browser.close()
    pw.stop()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=5, help='Max comments to post')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be posted without posting')
    args = parser.parse_args()
    main(max_comments=args.max, dry_run=args.dry_run)
