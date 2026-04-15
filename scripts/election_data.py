"""
Election data fetchers for whocanivotefor.co.uk and wheredoivote.co.uk.

These are the public APIs used to find upcoming elections and polling stations.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

WCIVF_BASE = os.getenv("WCIVF_BASE_URL", "https://whocanivotefor.co.uk")
WDIV_BASE = os.getenv("WDIV_BASE_URL", "https://wheredoivote.co.uk")


def get_elections_for_postcode(postcode: str) -> dict:
    """Query whocanivotefor.co.uk for upcoming elections by postcode.

    Returns the full API response dict including dates and ballot info.
    """
    url = f"{WCIVF_BASE}/api/candidates_for_postcode/"
    params = {"postcode": postcode}
    resp = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_candidates_for_ballot(ballot_paper_id: str) -> dict:
    """Fetch candidates for a specific ballot paper ID.

    Example ballot_paper_id: 'local.sheffield.beauchief-and-greenhill.2026-05-05'
    """
    url = f"{WCIVF_BASE}/api/candidates_for_ballots/"
    params = {"ballot_paper_id": ballot_paper_id}
    resp = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_upcoming_ballots(limit: int = 100) -> list[dict]:
    """Fetch a list of upcoming ballots from the WCIVF API.

    Returns ballot objects with election date, area, and ballot_paper_id.
    """
    url = f"{WCIVF_BASE}/api/candidates_for_ballots/"
    params = {"limit": limit}
    resp = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # The API may return paginated results with 'results' key
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def get_polling_station(postcode: str) -> dict | None:
    """Query wheredoivote.co.uk for polling station info by postcode.

    Returns dict with station address and opening times, or None if unavailable.
    """
    url = f"{WDIV_BASE}/api/beta/postcode/{postcode}/"
    resp = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()
