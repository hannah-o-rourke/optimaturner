"""
region.py — Map Facebook pages to their election region.

Regions:
- Scotland: Scottish Parliament election (all 129 seats)
- Wales: Senedd (Welsh Parliament) election (all 96 seats)
- England: Local council elections (5,014 seats across 136 councils)
"""

import csv
from pathlib import Path

PAGES_CSV = Path(__file__).resolve().parent.parent / "config" / "pages.csv"

# Outlets that are Scottish
SCOTTISH_OUTLETS = {
    "Daily Record", "The Herald (Glasgow)", "Glasgow Times",
    "The National (Scotland)", "The Scotsman", "Edinburgh News",
    "STV News", "Greenock Telegraph", "Falkirk Herald",
    "Fife Free Press", "Stornoway Gazette", "Cumbernauld News",
}

# Outlets that are Welsh
WELSH_OUTLETS = {
    "Wales Online", "South Wales Argus", "Daily Post Wales",
}


def get_region(outlet: str) -> str:
    """Return 'Scotland', 'Wales', or 'England' for a given outlet name."""
    if outlet in SCOTTISH_OUTLETS:
        return "Scotland"
    if outlet in WELSH_OUTLETS:
        return "Wales"
    return "England"


def election_type_for_region(region: str) -> str:
    """Return a human-readable election type string for the region."""
    if region == "Scotland":
        return "the Scottish Parliament election"
    if region == "Wales":
        return "the Senedd (Welsh Parliament) election"
    return "local council elections"


def election_label_for_outlet(outlet: str) -> str:
    """Return the election type string appropriate for a given outlet."""
    return election_type_for_region(get_region(outlet))
