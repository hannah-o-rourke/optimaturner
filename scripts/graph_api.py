"""
Facebook Graph API wrapper for Vote Uncovered.

Handles reading posts from monitored pages, posting comments/replies,
and publishing to the Vote Uncovered page.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

PAGE_ID = os.getenv("FB_PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")


class GraphAPIError(Exception):
    """Raised when a Graph API call fails."""
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response


def _headers():
    return {"Authorization": f"Bearer {PAGE_ACCESS_TOKEN}"}


def _check_response(resp, context="API call"):
    """Raise GraphAPIError if the response indicates failure."""
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            detail = resp.text
        raise GraphAPIError(f"{context} failed ({resp.status_code}): {detail}", resp)
    return resp.json()


# ── Read ────────────────────────────────────────────────────────────────

def get_page_posts(page_id: str, limit: int = 25) -> list[dict]:
    """Fetch recent posts from a public page.

    Returns list of dicts with keys: id, message, created_time, permalink_url.
    """
    url = f"{GRAPH_API_BASE}/{page_id}/posts"
    params = {
        "fields": "id,message,created_time,permalink_url",
        "limit": limit,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    data = _check_response(requests.get(url, params=params), f"get_page_posts({page_id})")
    return data.get("data", [])


def get_post_comments(post_id: str, limit: int = 100) -> list[dict]:
    """Fetch comments on a post. Returns list with id, from, message, created_time."""
    url = f"{GRAPH_API_BASE}/{post_id}/comments"
    params = {
        "fields": "id,from,message,created_time",
        "limit": limit,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    data = _check_response(requests.get(url, params=params), f"get_post_comments({post_id})")
    return data.get("data", [])


def get_comment_replies(comment_id: str, limit: int = 100) -> list[dict]:
    """Fetch replies to a specific comment."""
    url = f"{GRAPH_API_BASE}/{comment_id}/comments"
    params = {
        "fields": "id,from,message,created_time",
        "limit": limit,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    data = _check_response(requests.get(url, params=params), f"get_comment_replies({comment_id})")
    return data.get("data", [])


# ── Write ───────────────────────────────────────────────────────────────

def post_comment(post_id: str, message: str) -> dict:
    """Post a comment on a post. Returns the new comment's data (id)."""
    url = f"{GRAPH_API_BASE}/{post_id}/comments"
    payload = {"message": message, "access_token": PAGE_ACCESS_TOKEN}
    return _check_response(requests.post(url, data=payload), f"post_comment({post_id})")


def post_reply(comment_id: str, message: str) -> dict:
    """Reply to an existing comment. Returns the new reply's data (id)."""
    url = f"{GRAPH_API_BASE}/{comment_id}/comments"
    payload = {"message": message, "access_token": PAGE_ACCESS_TOKEN}
    return _check_response(requests.post(url, data=payload), f"post_reply({comment_id})")


def publish_to_page(message: str) -> dict:
    """Publish a new post to the Vote Uncovered page. Returns post data (id)."""
    url = f"{GRAPH_API_BASE}/{PAGE_ID}/feed"
    payload = {"message": message, "access_token": PAGE_ACCESS_TOKEN}
    return _check_response(requests.post(url, data=payload), f"publish_to_page")
