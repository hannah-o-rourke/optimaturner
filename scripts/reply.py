#!/usr/bin/env python3
"""
reply.py — Check and respond to replies on Vote Uncovered's comments.

Loads commented posts from data/commented.json, fetches replies to our comments,
and responds helpfully. Tracks replied-to comment IDs to avoid double-replying.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from graph_api import get_comment_replies, post_reply, GraphAPIError, PAGE_ID
from action_logger import log_action

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMENTED_FILE = DATA_DIR / "commented.json"
REPLIED_FILE = DATA_DIR / "replied.json"

# ── Reply templates ─────────────────────────────────────────────────────

HELPFUL_REPLIES = {
    "where": (
        "Great question! You can find your polling station by entering your "
        "postcode at wheredoivote.co.uk — it'll tell you exactly where to go "
        "and when it's open. 🗳️"
    ),
    "when": (
        "Local elections are on Thursday, May 5th 2026! Polling stations are "
        "open from 7am to 10pm. You can find yours at wheredoivote.co.uk 🗳️"
    ),
    "register": (
        "You can register to vote online at gov.uk/register-to-vote — it only "
        "takes about 5 minutes! The deadline to register for the May elections "
        "is usually about 2 weeks before polling day. 🗳️"
    ),
    "who": (
        "You can see exactly who's standing in your area by entering your "
        "postcode at whocanivotefor.co.uk — it lists all the candidates "
        "for your local elections. 🗳️"
    ),
    "default": (
        "Thanks for your interest! If you'd like to find out more about "
        "your local elections, whocanivotefor.co.uk is a great place to start. "
        "Every vote counts at the local level! 🗳️"
    ),
}

# Hostile/troll indicators — respond once politely, then disengage
HOSTILE_INDICATORS = [
    "shut up", "spam", "bot", "scam", "f*** off", "piss off",
    "nobody cares", "waste of time", "get lost",
]

POLITE_DISENGAGE = (
    "We're just here to help people find info about their local elections — "
    "no agenda, just making sure everyone knows they can have their say! "
    "Have a great day 😊"
)


def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_json(path: Path, data: dict):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def classify_reply(text: str) -> str:
    """Determine the type of reply to give based on the incoming message."""
    lower = text.lower()

    # Check for hostile content first
    for indicator in HOSTILE_INDICATORS:
        if indicator in lower:
            return "hostile"

    # Check for question types
    if any(w in lower for w in ["where do i vote", "polling station", "where to vote"]):
        return "where"
    if any(w in lower for w in ["when", "what date", "what day", "polling day"]):
        return "when"
    if any(w in lower for w in ["register", "sign up", "how do i vote"]):
        return "register"
    if any(w in lower for w in ["who", "candidate", "standing", "running"]):
        return "who"

    return "default"


def handle_replies():
    """Check all our comments for new replies and respond."""
    commented = load_json(COMMENTED_FILE)
    replied = load_json(REPLIED_FILE)
    if "replies" not in replied:
        replied["replies"] = {}

    posts = commented.get("posts", {})
    if not posts:
        log_action("reply", "No commented posts to check for replies.")
        print("No commented posts to check.")
        return

    replies_sent = 0
    log_action("reply", f"Checking replies on {len(posts)} commented posts")

    for post_id, info in posts.items():
        comment_id = info.get("comment_id")
        if not comment_id:
            continue

        try:
            replies_list = get_comment_replies(comment_id)
        except GraphAPIError as e:
            log_action("reply", f"ERROR fetching replies for {comment_id}: {e}")
            continue

        for reply_msg in replies_list:
            reply_id = reply_msg.get("id", "")
            # Skip if already replied to
            if reply_id in replied["replies"]:
                continue

            # Skip our own replies
            from_user = reply_msg.get("from", {})
            if from_user.get("id") == PAGE_ID:
                continue

            author_name = from_user.get("name", "Unknown")
            reply_text = reply_msg.get("message", "")

            # Log incoming reply
            log_action(
                "reply",
                f"Incoming reply from {author_name}",
                comment_id=comment_id,
                reply_id=reply_id,
                reply_text=reply_text,
            )

            # Classify and respond
            reply_type = classify_reply(reply_text)

            if reply_type == "hostile":
                # Check if we already sent a polite disengage to this thread
                thread_hostile_key = f"hostile_{comment_id}"
                if thread_hostile_key in replied["replies"]:
                    log_action("reply", f"SKIP: Already disengaged from hostile thread {comment_id}")
                    replied["replies"][reply_id] = {"skipped": True, "reason": "already_disengaged"}
                    continue
                response_text = POLITE_DISENGAGE
                replied["replies"][thread_hostile_key] = True
            else:
                response_text = HELPFUL_REPLIES.get(reply_type, HELPFUL_REPLIES["default"])

            try:
                result = post_reply(reply_id, response_text)
                our_reply_id = result.get("id", "unknown")

                replied["replies"][reply_id] = {
                    "our_reply_id": our_reply_id,
                    "reply_type": reply_type,
                    "replied_at": datetime.utcnow().isoformat() + "Z",
                }
                replies_sent += 1

                log_action(
                    "reply",
                    f"Replied to {author_name} ({reply_type})",
                    parent_comment_id=comment_id,
                    their_reply_id=reply_id,
                    our_reply_id=our_reply_id,
                    their_text=reply_text,
                    our_text=response_text,
                )

            except GraphAPIError as e:
                log_action("reply", f"ERROR replying to {reply_id}: {e}")

    save_json(REPLIED_FILE, replied)
    log_action("reply", f"Reply run complete. {replies_sent} replies sent.")
    print(f"Reply complete: {replies_sent} replies sent.")


if __name__ == "__main__":
    handle_replies()
