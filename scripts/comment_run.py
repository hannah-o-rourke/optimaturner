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
    # Hyperlocal issues — the bread and butter of council work
    "pothole", "potholes", "road repair", "roadworks",
    "parking", "parking ticket", "parking warden", "double yellow",
    "bin", "bins", "rubbish", "waste", "recycling", "fly tipping", "flytipping", "fly-tipping",
    "housing", "council house", "social housing", "rent", "tenant", "affordable home",
    "planning", "planning permission", "development", "building", "regeneration",
    "park", "playground", "green space", "allotment",
    "bus", "bus route", "bus service", "bus stop", "transport", "cycle lane", "cycling",
    "high street", "town centre", "shop closure", "empty shop",
    "flooding", "flood", "drains", "sewage",
    "library", "leisure centre", "swimming pool", "community centre",
    "pavement", "footpath", "streetlight", "street light",
    "council tax", "council budget", "council cut",
    "councillor", "local council",
    "residents", "petition", "neighbourhood",
    "school place", "school closure",
    "speed limit", "speed camera", "road safety",
    "litter", "graffiti", "antisocial", "anti-social",
    "homeless", "homelessness", "rough sleep",
    "air quality", "pollution", "noise complaint",
]

SKIP_TOPICS = [
    # National politics
    "westminster", "parliament", "prime minister", "starmer", "sunak",
    "general election", "national",
    # Entertainment / lifestyle
    "celebrity", "premier league", "champions league", "world cup",
    "love island", "strictly", "weather forecast", "recipe", "quiz",
    "restaurant", "ice cream", "beer garden", "café", "cafe",
    # Sensitive subjects — NEVER comment on these
    "death", "died", "killed", "fatal", "murder", "manslaughter",
    "suicide", "inquest", "coroner", "funeral", "tragedy", "tragic",
    "rape", "sexual assault", "abuse", "child abuse", "paedophile",
    "pedophile", "missing person", "missing child", "stabbing", "stabbed",
    "shooting", "terror", "terrorist", "cancer", "terminal",
    "crash victim", "victim", "mourning", "tribute", "rip",
    "sentenced", "jailed", "prison", "court case", "guilty",
]

def is_relevant(text):
    lower = text.lower()
    if any(skip in lower for skip in SKIP_TOPICS):
        return False
    return any(kw in lower for kw in LOCAL_ISSUE_KEYWORDS)

def get_election_type(page_name):
    """Returns (election_name, verb_form) — e.g. ('the Senedd election', 'is') or ('local council elections', 'are')"""
    if any(w in page_name for w in WELSH_PAGES):
        return "the Senedd election", "is"
    if any(s in page_name for s in SCOTTISH_PAGES):
        return "the Scottish Parliament election", "is"
    return "local council elections", "are"

def craft_comment(post_text, page_name):
    """Generate a natural, contextual comment that responds to the specific post."""
    election, verb = get_election_type(page_name)
    lower = post_text.lower()

    # Extract a place name if present (look for capitalised words near local keywords)
    place_match = re.search(r'\b(in|across|around|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', post_text)
    place = place_match.group(2) if place_match else ''

    # Detect specific topic and craft a unique opener that references the actual content
    if any(w in lower for w in ['pothole', 'road', 'traffic', 'bus', 'parking', 'cycling', 'transport']):
        openers = [
            f"Potholes and road repairs" if 'pothole' in lower else
            f"Bus services" if 'bus' in lower else
            f"Traffic and parking" if any(w in lower for w in ['traffic','parking']) else
            f"Transport and roads",
        ]
        opener = openers[0]
        place_bit = f" in {place}" if place else ''
        comments = [
            f"{opener}{place_bit} — this is exactly what your local councillors deal with day to day. {election.capitalize() if election[0]!='t' else election} {verb} on May 7th and the people you pick will decide how this gets handled. Two minutes to check who's standing in your area: whocanivotefor.co.uk",
            f"Frustrating to see{place_bit}. Worth knowing your council controls this stuff directly. With {election} on May 7th you actually get a say in who fixes it (or doesn't). Have a look: whocanivotefor.co.uk",
            f"This is one of those things that feels small but affects everyone{place_bit}. {election} {verb} two weeks away on May 7th — your vote picks who's responsible for sorting it. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['housing', 'rent', 'tenant', 'eviction', 'homeless']):
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Housing{place_bit} is such a massive issue right now and a lot of the decisions happen at the local level. {election} {verb} on May 7th — worth seeing what candidates in your area are saying about it: whocanivotefor.co.uk",
            f"Stories like this show why local elections matter. Councils make real housing decisions that affect real people{place_bit}. May 7th is {election} — takes two minutes to look up who's standing: whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['bin', 'rubbish', 'waste', 'recycling', 'litter', 'fly-tip', 'flytip']):
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Nothing winds people up quite like bins{place_bit} 😅 But seriously, this is 100% a local council responsibility. {election} {verb} on May 7th and your councillors are the ones who decide how waste gets handled. Check who's standing: whocanivotefor.co.uk",
            f"Waste collection{place_bit} is one of those services you only notice when it goes wrong. Your local council runs it, and {election} on May 7th decides who's in charge. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['police', 'crime', 'antisocial', 'anti-social', 'stabbing', 'robbery']):
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Really concerning{place_bit}. Community safety is something your elected local representatives can push for — more funding, better services, actual accountability. {election} {verb} on May 7th. See who's standing and what they'd do: whocanivotefor.co.uk",
            f"Nobody should have to put up with this{place_bit}. If you want things to change, {election} on May 7th is a real opportunity to pick people who'll prioritise safety. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['council', 'councillor', 'council tax', 'budget', 'funding', 'cut']):
        place_bit = f" to {place}" if place else ''
        comments = [
            f"These are exactly the decisions that get made in {election}. May 7th is coming up — if you want different choices being made{place_bit}, that's your moment. See who's standing: whocanivotefor.co.uk",
            f"Council budgets affect everything from your bins to your kids' schools{place_bit}. {election} {verb} on May 7th and you get to choose who holds the purse strings. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['park', 'green space', 'playground', 'leisure', 'library', 'community centre']):
        thing = 'libraries' if 'library' in lower or 'libraries' in lower else 'parks' if 'park' in lower else 'community spaces' if 'community' in lower else 'local facilities'
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Love that people care about {thing}{place_bit}. Your council manages these and {election} on May 7th decides who's looking after them. Quick check on who's standing in your area: whocanivotefor.co.uk",
            f"{thing.capitalize()}{place_bit} are one of those things that make a neighbourhood. They're run by your council, and {election} {verb} on May 7th. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['school', 'education', 'teacher', 'pupil']):
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Education{place_bit} is shaped by local decisions more than most people realise. {election} {verb} on May 7th — if schools matter to you, it's worth checking who's standing: whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['planning', 'development', 'regeneration', 'building', 'demolish']):
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Planning decisions{place_bit} are made by your local council and they shape what your area looks like for decades. {election} {verb} on May 7th — pick who makes these calls. whocanivotefor.co.uk",
            f"Whether you're for or against developments like this{place_bit}, the people who approve them are chosen in {election}. May 7th is your say. whocanivotefor.co.uk",
        ]
    elif any(w in lower for w in ['flood', 'environment', 'pollution', 'air quality', 'climate']):
        place_bit = f" in {place}" if place else ''
        comments = [
            f"Environmental issues{place_bit} often come down to local decisions — drainage, planning, green spaces, air quality monitoring. {election} {verb} on May 7th and you get to choose who prioritises this. whocanivotefor.co.uk",
        ]
    else:
        place_bit = f" in {place}" if place else ''
        comments = [
            f"This is the kind of local issue that actually gets decided by the people you vote for. {election} {verb} on May 7th{place_bit} — takes a couple of minutes to see who's standing: whocanivotefor.co.uk",
            f"Stuff like this is exactly why {election} matter{'' if verb == 'is' else 's'}. May 7th{place_bit} — have a look who's on your ballot: whocanivotefor.co.uk",
        ]

    return random.choice(comments)

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
    ctx.storage_state(path=str(PROJECT_ROOT / 'data' / 'browser_state.json'))  # backup
    
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
