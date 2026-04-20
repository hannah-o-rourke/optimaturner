# Vote Uncovered 🗳️

**Non-partisan civic engagement bot for UK local elections.**

An autonomous agent that monitors community Facebook pages, identifies posts about local issues, and comments to remind residents about upcoming local elections. Also publishes daily content to the [Vote Uncovered Facebook page](https://facebook.com/voteuncovered).

Built for [Campaign Lab](https://www.campaignlab.uk/). Target: **UK elections, 7 May 2026** — local council elections in England (5,014 seats across 136 councils), the Senedd election in Wales (96 seats), and the Scottish Parliament election in Scotland (129 seats).

## How It Works

The daily pipeline runs four steps:

1. **sync-elections** — Fetches upcoming election data from [whocanivotefor.co.uk](https://whocanivotefor.co.uk)
2. **monitor** — Scans 110+ local news Facebook pages for posts about local issues, comments with election reminders
3. **post** — Publishes daily content to the Vote Uncovered page
4. **reply** — Checks replies to our comments, responds helpfully with voter info

## Setup

```bash
# 1. Clone and install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your Facebook Page ID and access token

# 3. Run the daily pipeline
bash scripts/run.sh
```

## Cron (VPS deployment)

```cron
0 9 * * * /path/to/scripts/run.sh
```

## Project Structure

```
├── scripts/
│   ├── run.sh              # Daily entrypoint
│   ├── sync_elections.py   # Fetch election data
│   ├── monitor.py          # Watch pages, comment on local-issue posts
│   ├── post.py             # Publish to Vote Uncovered page
│   ├── reply.py            # Respond to replies on our comments
│   ├── graph_api.py        # Facebook Graph API wrapper
│   ├── election_data.py    # whocanivotefor + wheredoivote API fetchers
│   └── action_logger.py    # Append-only audit logging
├── config/
│   └── pages.csv           # 110+ monitored Facebook pages
├── data/                   # Runtime data (gitignored)
├── logs/                   # Action + run logs (gitignored)
├── .env.example
├── requirements.txt
└── SPEC.md                 # Full project specification
```

## Guardrails

- ❌ Never mentions specific candidates or parties
- ❌ Never comments on national politics
- ❌ Never tells people *who* to vote for
- ❌ Never comments on the same post twice
- ❌ Never engages with trolls beyond one polite response
- ✅ UK local elections only
- ✅ Encouraging, non-partisan, helpful

## Data Sources

- [whocanivotefor.co.uk](https://whocanivotefor.co.uk) — Upcoming elections by area
- [wheredoivote.co.uk](https://wheredoivote.co.uk) — Polling station info
- [gov.uk/register-to-vote](https://gov.uk/register-to-vote) — Voter registration

## Audit

All actions are logged to:
- `logs/comments.csv` — Every comment posted, with timestamps, page name, post URL, and full text ([view on GitHub](logs/comments.csv))
- `logs/actions.log` — Detailed action log with capability tags

See [SPEC.md](SPEC.md) for details.

## Status

✅ **Pilot live** (20 April 2026) — First successful external page comment posted on Bristol Post via browser automation.

10 approved news pages across England, Wales, and Scotland. Comments posted as Dominic O'Cratic with permission from page administrators.
