# Vote Uncovered: Proof of Concept Report
### Automated Social Media Campaigning — Electoral Commission Submission

**Project:** Vote Uncovered  
**Organisation:** Campaign Lab  
**Author:** Hannah O'Rourke  
**Period:** 15 April – 7 May 2026  
**Elections covered:** England local councils, Wales Senedd, Scotland Parliament (all 7 May 2026)

---

## Purpose

This project was built as a proof of concept to demonstrate to the Electoral Commission how automated social media campaigning on Facebook can be set up cheaply, quickly, and with minimal technical expertise — and why it requires regulatory attention.

The campaign was non-partisan: its sole aim was to encourage voter turnout by commenting on hyperlocal news stories, reminding readers that local elections were happening and directing them to whocanivotefor.co.uk to find their candidates.

---

## What We Built

An AI agent (running on a standard cloud server) that:

1. **Monitored over 110 local news Facebook pages** across England, Wales and Scotland
2. **Browsed Facebook's home feed** as a human-like account (following local news pages)
3. **Read and assessed posts** for relevance — filtering for genuinely hyperlocal stories (potholes, housing, school funding, bus services, social care etc.)
4. **Wrote contextual, unique comments** responding to the specific story — not templates
5. **Posted comments** on those stories, linking to election resources
6. **Logged every action** with timestamps, post URLs and comment text for full auditability

The entire system was built in approximately **three weeks**, by one person with the assistance of an AI coding assistant, at **near-zero cost** beyond a standard cloud server subscription.

---

## Technical Approach

### Phase 1: Graph API (abandoned)
Initial design used Facebook's official Graph API to post comments programmatically. This was abandoned when it became clear that:
- Access tokens require Facebook app review for publishing permissions
- The review process is slow and not guaranteed

**Time to reach this conclusion:** ~2 days

### Phase 2: Browser Automation with Playwright
We pivoted to browser automation — controlling a real web browser programmatically to interact with Facebook as a logged-in user. This is the same technology used by web testing frameworks and is freely available.

Key technical challenges overcome:
- **Cookie consent dialogs:** Facebook uses non-standard `[role="button"]` div elements, not standard `<button>` elements
- **Dynamic IDs:** Login form field IDs change on each load — required attribute-based selectors
- **React UI:** Facebook's comment submission ignores standard synthetic click events — required dispatching low-level mouse event sequences (pointerdown, mousedown, pointerup, mouseup, click) via JavaScript injection
- **Modal dialogs:** Overlay dialogs block interaction and must be removed via JavaScript before commenting
- **Home feed vs. page feed:** Page feeds do not render interactive comment boxes — comments can only be posted via the home feed modal

None of these are advanced exploits. They are documented, publicly known patterns used by browser automation tools worldwide.

**Time to get first working comment posted:** ~3 days of iteration

### Phase 3: AI-Judged Commenting
Early versions used keyword matching to decide which posts to comment on. This caused at least one error where a comment was placed on an irrelevant post. 

We switched to a human-in-the-loop approach where the AI agent reads and evaluates every post before deciding to comment — applying genuine contextual understanding rather than pattern matching.

**Comment quality criteria:**
- Must be genuinely hyperlocal (potholes, housing, bins, transport, schools, social care, planning)
- Must respond to the specific story, not paste a generic message
- Must never comment on: death, crime, court cases, tragedies, national politics, entertainment, sport
- Must be appropriate for the community the page serves (Welsh pages → Senedd election messaging; Scottish pages → Scottish Parliament)

---

## Accounts Used

### Account 1: Dominic O'Cratic
- Created for the project
- Used 20–22 April 2026
- **Suspended by Facebook on 24 April 2026** — no right of appeal offered
- 21 comments logged before suspension

Facebook's automated systems detected the account within approximately **4 days of operation**.

### Account 2: Polly Ticks
- New account set up 27 April 2026
- Email: hannahelisabethorourke@gmail.com
- Warmup phase: followed pages, reacted to posts, built normal-looking activity pattern
- Active commenting phase began ~29 April 2026
- **127 comments logged** between 29 April and 6 May 2026
- Facebook session periodic interruptions required manual re-verification (video verification, login checkpoints) — approximately every 7–10 days

---

## Volume and Reach

| Metric | Value |
|--------|-------|
| Total comments posted | 127 (as of 6 May 2026) |
| Facebook pages targeted | 110+ monitored; ~25 actively commented on |
| Date range | 20 April – 6 May 2026 |
| Countries/devolved nations | England, Wales, Scotland |
| Accounts used | 2 (one suspended) |
| Cost of operation | ~£5/month server costs |
| Development time | ~3 weeks (part-time) |

### Most Targeted Pages
- WalesOnline (7 comments)
- Derbyshire Times (7)
- Leicestershire Live (5)
- Berkshire Live (5)
- Bristol Live (4)
- Stoke-on-Trent Live (4)
- KentLive (4)

### Topics Covered
Potholes and road repairs, housing and planning, school funding and SEND, bus services and transport, council tax, waste and recycling, parks and green spaces, flooding, social care cuts, empty high street buildings, community spaces, RAAC in schools, affordable homes.

---

## Key Findings for the Electoral Commission

### 1. The barrier to entry is extremely low
Building a system capable of posting targeted political messaging to 110+ local Facebook pages required:
- One person
- Three weeks (part-time)
- Free/open-source software (Python, Playwright)
- A standard cloud server (~£5/month)
- No specialist knowledge beyond basic programming

A well-resourced political campaign, foreign state actor, or commercial operator could build something significantly more sophisticated at minimal cost.

### 2. Facebook's defences are not robust enough
Facebook's automated detection suspended one account within 4 days. However:
- A second account with a brief warmup period operated undetected for 10+ days
- The warmup strategy (liking posts, following pages gradually, varying timing) is publicly documented
- There is no meaningful technical barrier to creating multiple accounts simultaneously and running them in parallel

### 3. Volume can be significant
127 comments across 25 news pages in ~10 days represents a modest proof of concept. A scaled operation using multiple accounts, running 24/7, could potentially reach hundreds of thousands of readers through comment sections on high-traffic local news pages.

### 4. Comments appear organic
The AI-generated comments were contextual, specific to each story, and written in a natural voice. Without knowing the system existed, readers would have no way to identify them as automated. There is no disclosure requirement or mechanism for automated political commenting on Facebook.

### 5. The targeting capability is sophisticated
The system could be extended to target by:
- **Geography:** Comment only on pages covering marginal seats
- **Demographics:** Follow pages serving specific demographics
- **Timing:** Post at peak engagement times for each page
- **Content:** Respond to trending local topics with partisan messaging

Our implementation used all of these capabilities in a non-partisan way. A partisan actor would face no technical barriers to doing the same with political messaging.

### 6. Traceability is limited
Facebook does not provide public data on how many automated accounts are operating, what they're posting, or how many people have seen their content. The only transparency in this project exists because we built our own audit trail — there is no platform-mandated equivalent.

---

## Problems and Obstacles We Encountered

This section documents the genuine difficulties we hit — relevant to the EC because it illustrates both the *real* barriers and how easy they were to overcome.

### 1. Facebook's Graph API access was effectively blocked
Our original plan was to use Facebook's official API to post comments. We applied for the necessary permissions but Facebook's app review process is opaque and slow. We abandoned this after ~2 days when it became clear we'd never get publishing access in time. The pivot to browser automation was trivial.

### 2. Browser automation required significant reverse-engineering
Facebook's UI is a heavily optimised React application and resists standard automation:
- **Cookie consent:** Used non-standard div elements with `role="button"` instead of `<button>` — took several iterations to find
- **Dynamic IDs:** Field IDs on the login form regenerate on each page load — broke ID-based selectors immediately
- **Comment submission:** The "Post comment" button completely ignores Playwright's standard `.click()` method. Facebook's React event handlers only fire on low-level browser events. We had to inject JavaScript to dispatch a manual sequence of `pointerdown → mousedown → pointerup → mouseup → click` events. This took approximately a day to diagnose and fix.
- **Dialog overlays:** Facebook frequently overlays modals that block interaction. We had to remove these via JavaScript injection before every action.
- **Page feed vs. home feed:** We spent several hours trying to post comments directly from a page's own feed (e.g. facebook.com/bristollive) before discovering that Facebook doesn't render interactive comment boxes there — only on the home feed modal. This was a significant time loss.
- **Textbox selectors:** The comment textbox `aria-label` changed between sessions (capitalisation, ellipsis characters). We ultimately had to switch to a selector based on element role/contenteditable attributes rather than aria-label.

### 3. First account suspended within 4 days
The Dominic O'Cratic account was suspended on 24 April 2026 with no warning and no right of appeal. Facebook gave no specific reason. This was a significant setback — we lost all the page follows and account history built up over the warmup period. We had to start from scratch with a new identity (Polly Ticks).

### 4. Session management and re-verification
Facebook treats server IP addresses as "new devices" and periodically requires re-verification even when 2FA is disabled. This meant the automation would silently fail (redirecting to a checkpoint page) until we manually intervened. Recovery required:
- Exporting cookies from a real browser session using a browser extension (Cookie-Editor)
- Converting them to Playwright's storage format
- Reinjecting them into the automation

This happened approximately every 7–10 days and required Hannah to log in manually and export cookies each time, including video verification on at least one occasion.

### 5. Feed quality and timing
Polly's account was new, so Facebook's algorithm initially served very little local news in the home feed — mostly national content, sport and lifestyle. We had to:
- Spend several days in a "warmup" phase: following pages, liking local news posts, building engagement history
- Supplement home feed scrolling with direct page visits when the feed was thin
- Accept that bank holidays and weekends produced significantly fewer usable hyperlocal stories

### 6. Context-aware commenting was harder than expected
Early automated scripts used keyword matching to decide what to comment on. This caused at least one incident where a comment landed on an inappropriate post (a comment about local shops appeared on an unrelated lifestyle article). We switched to a human-in-the-loop model where the AI reads and evaluates each post before deciding — this worked well but required the AI to remain in the loop for every session rather than running fully unattended.

### 7. Scale vs. detection tradeoff
Posting too many comments too quickly risks detection and suspension. We throttled to approximately 8–15 comments per session, with randomised delays between actions (20–40ms typing speed, 3–8 second pauses between comments). This is a standard anti-detection pattern that any automated system would implement.

---

## What Regulation Could Address

1. **Disclosure requirements:** Automated accounts posting political content should be required to identify themselves as bots, similar to rules in some US states
2. **Platform transparency:** Social media platforms should be required to detect and report automated political activity to electoral regulators
3. **Spending rules:** Automated social media campaigning should be treated as campaign expenditure, even when using free tools — the reach and persuasion potential is equivalent to paid advertising
4. **Account verification:** Stricter identity verification for accounts posting on political topics, particularly during election periods

---

## Audit Trail

All comments are logged with full metadata in `logs/comments.csv`:
- Timestamp (UTC)
- Account name
- Activity type
- Page name
- Page URL
- Post URL
- Full comment text

The full codebase is available at: https://github.com/hannah-o-rourke/optimaturner

---

*This project was conducted as a proof of concept for research and regulatory purposes. All content was non-partisan and designed to increase voter participation, not to advantage any party or candidate.*
