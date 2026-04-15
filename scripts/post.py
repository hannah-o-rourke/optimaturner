#!/usr/bin/env python3
"""
post.py — Generate and publish daily content to the Vote Uncovered Facebook page.

Reads cached election data and creates an engaging, non-partisan post about
upcoming local elections.
"""

import json
import os
import random
import sys
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from graph_api import publish_to_page, GraphAPIError
from action_logger import log_action

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ELECTIONS_FILE = DATA_DIR / "elections.json"
POSTED_FILE = DATA_DIR / "posted.json"

# Days before election to start ramping up
RAMP_UP_DAYS = 14
ELECTION_DATE = date(2026, 5, 5)


def load_elections() -> dict:
    if ELECTIONS_FILE.exists():
        return json.loads(ELECTIONS_FILE.read_text())
    return {}


def load_posted() -> dict:
    if POSTED_FILE.exists():
        return json.loads(POSTED_FILE.read_text())
    return {"posts": []}


def save_posted(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    POSTED_FILE.write_text(json.dumps(data, indent=2))


def days_until_election() -> int:
    return (ELECTION_DATE - date.today()).days


def generate_post_content(elections: dict) -> str:
    """Generate today's post content based on election data and countdown."""
    days_left = days_until_election()
    num_ballots = elections.get("local_ballots", 0)

    # Extract some area names for variety
    ballots = elections.get("ballots", [])
    areas = set()
    for b in ballots[:50]:
        # ballot_paper_id like 'local.sheffield.beauchief-and-greenhill.2026-05-05'
        parts = b.get("ballot_paper_id", "").split(".")
        if len(parts) >= 2:
            area = parts[1].replace("-", " ").title()
            areas.add(area)
    area_sample = random.sample(list(areas), min(3, len(areas))) if areas else []

    if days_left <= 0:
        return (
            "🗳️ It's polling day! If you haven't voted yet, there's still time — "
            "polls are open until 10pm.\n\n"
            "Find your polling station: wheredoivote.co.uk\n\n"
            "Your vote matters. Make it count! 🗳️\n\n"
            "#LocalElections #YourVoteMatters"
        )

    if days_left == 1:
        return (
            "🗳️ TOMORROW is polling day!\n\n"
            "Local elections are happening across the UK tomorrow, Thursday May 5th. "
            "Polls open at 7am and close at 10pm.\n\n"
            "✅ Find your polling station: wheredoivote.co.uk\n"
            "✅ See who's standing: whocanivotefor.co.uk\n"
            "✅ Remember to bring photo ID!\n\n"
            "Your local councillors make decisions about your area every single day. "
            "Make sure you have your say! 🗳️\n\n"
            "#LocalElections #VoteTomorrow"
        )

    if days_left <= 7:
        return (
            f"🗳️ Just {days_left} days until local elections!\n\n"
            f"On Thursday May 5th, voters across the UK will choose their local councillors. "
            f"That's the people who decide on planning, housing, roads, schools, and so much more "
            f"in your area.\n\n"
            + (f"Elections are happening in areas including {', '.join(area_sample)} and many more.\n\n" if area_sample else "")
            + "✅ Check who's standing in your area: whocanivotefor.co.uk\n"
            "✅ Find your polling station: wheredoivote.co.uk\n"
            "✅ Make sure you're registered: gov.uk/register-to-vote\n\n"
            "Every vote counts at the local level! 🗳️\n\n"
            "#LocalElections #YourVoteMatters"
        )

    if days_left <= RAMP_UP_DAYS:
        templates = [
            (
                f"🗳️ Local elections are {days_left} days away!\n\n"
                f"There are {num_ballots}+ local elections happening across the UK on May 5th. "
                "These elections decide who runs your local council — the people in charge of "
                "everything from bin collections to housing decisions.\n\n"
                + (f"Areas voting include: {', '.join(area_sample)}\n\n" if area_sample else "")
                + "Find out what's happening in your area: whocanivotefor.co.uk 🗳️\n\n"
                "#LocalElections #VoteLocal"
            ),
            (
                f"📢 {days_left} days to go!\n\n"
                "Did you know your local councillors have more impact on your daily life "
                "than most MPs? They decide on:\n\n"
                "🏠 Housing and planning\n"
                "🚍 Local transport\n"
                "🗑️ Waste and recycling\n"
                "🌳 Parks and green spaces\n"
                "📚 Libraries and community services\n\n"
                "Local elections are on May 5th. Make sure you're ready to vote!\n"
                "whocanivotefor.co.uk 🗳️\n\n"
                "#LocalElections #VoteLocal"
            ),
        ]
        return random.choice(templates)

    # Standard daily post (more than 2 weeks out)
    templates = [
        (
            "🗳️ Local elections are coming to the UK on May 5th 2026!\n\n"
            f"There are {num_ballots}+ council seats being contested across the country. "
            "Your local council makes decisions that affect your everyday life — "
            "from potholes to parks, housing to high streets.\n\n"
            "Want to know if there's an election in your area? "
            "Check whocanivotefor.co.uk\n\n"
            "#LocalElections #VoteLocal #YourVoiceMatters"
        ),
        (
            "🏘️ Ever wondered who decides what happens on your street?\n\n"
            "Your local councillors! And you get to pick them in the upcoming "
            "local elections on May 5th.\n\n"
            "Find out who's standing in your area: whocanivotefor.co.uk\n"
            "Make sure you're registered: gov.uk/register-to-vote\n\n"
            "🗳️ Your vote, your community, your choice.\n\n"
            "#LocalElections"
        ),
    ]
    return random.choice(templates)


def post_daily():
    """Generate and publish today's post."""
    today = date.today().isoformat()
    posted = load_posted()

    # Check if we already posted today
    if any(p.get("date") == today for p in posted.get("posts", [])):
        log_action("post", f"SKIP: Already posted today ({today})")
        print(f"Already posted today ({today}). Skipping.")
        return

    elections = load_elections()
    if not elections:
        log_action("post", "SKIP: No election data available. Run sync_elections first.")
        print("No election data. Run sync_elections.py first.")
        return

    content = generate_post_content(elections)

    try:
        result = publish_to_page(content)
        post_id = result.get("id", "unknown")

        posted["posts"].append({
            "date": today,
            "post_id": post_id,
            "content": content,
            "posted_at": datetime.utcnow().isoformat() + "Z",
        })
        save_posted(posted)

        log_action(
            "post",
            f"Published daily post to Vote Uncovered page",
            post_id=post_id,
            post_text=content,
        )
        print(f"Posted to page: {post_id}")

    except GraphAPIError as e:
        log_action("post", f"ERROR publishing post: {e}")
        raise


if __name__ == "__main__":
    post_daily()
