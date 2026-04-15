  Vote Uncovered — OpenClaw Facebook Agent

  Full Project Spec v1.0

  ---
  Overview

  An autonomous OpenClaw agent that runs the Vote Uncovered Facebook Page on behalf of Campaign Lab. It monitors a curated list of UK community Facebook
  pages, identifies posts about local issues, and comments to remind residents about upcoming local elections. It also posts original content to its own
  page. Fully autonomous, daily cadence, non-partisan.

  ---
  Agent Identity

  | Field   | Value                                                |
  |---------|------------------------------------------------------|
  | Page    | facebook.com/voteuncovered                           |
  | Org     | Campaign Lab                                         |
  | Mission | Non-partisan voter turnout and civic participation |
  | Tone    | Cheery, helpful, encouraging                           |
  | Scope   | UK local elections only                              |

  ---
  Capabilities

  1. monitor — Watch & Comment

  - Polls curated list of community Facebook pages daily for new posts
  - Identifies posts discussing local issues (planning, housing, transport, schools, environment, NHS, etc.)
  - Posts a comment reminding people about upcoming local elections in their area
  - Derives the likely location/constituency from the page's profile and content
  - Queries whocanivotefor.co.uk to confirm whether a local election is upcoming for that area
  - Comment makes the case for why to vote — civic voice, having your say — never who to vote for

  2. reply — Respond to Comments

  - Checks replies on the comments posted by itself (Refer to list of facebook pages CSV)
  - Responds in a helpful, cheery tone
  - Answers questions about where/when to vote using wheredoivote.co.uk
  - Stays on-topic: redirects off-topic replies gracefully

  1. post — Own Page Content

  - Posts daily content to the Vote Uncovered page
  - Content: upcoming local elections in the UK, sourced from whocanivotefor.co.uk
  - Format: clear, readable, encouraging — not a data dump

  4. sync-elections — Refresh Election Data

  - Fetches upcoming UK local elections from whocanivotefor.co.uk
  - Stores locally for use by monitor and post
  - Runs daily before monitor and post

  ---
  Data Sources

  | Source               | URL                  | Used for                                 |
  |----------------------|----------------------|------------------------------------------|
  | Where Do I Vote      | wheredoivote.co.uk   | Polling station info for replies         |
  | Who Can I Vote For   | whocanivotefor.co.uk | Upcoming elections by area               |
  | Curated pages list   | config/pages.txt     | Pages to monitor (maintained manually)   |

  ---
  Scheduling

  | Trigger                 | Action                                                           |
  |-------------------------|------------------------------------------------------------------|
  | Daily                   | sync-elections → monitor → post → reply                          |
  | Pre-election ramp-up    | Increase comment frequency in final 2 weeks before an election |
  | Post-election cool-down | Pause comments for that area after election day passes           |

  ---
  Action log (monitoring & review)

  Every action the OpenClaw agent and supporting scripts take must be written to an append-only log file under `logs/` (for example `logs/actions.log`) so
  anyone can review what happened without using the Facebook UI alone.

  The log must be detailed enough for audit and trust: timestamp, which capability ran (sync-elections, monitor, post, reply), and stable identifiers from
  the Graph API where available (post id, comment id, page id).

  Required content

  - Outbound actions — Full verbatim text for every comment the agent posts on other pages, every reply the agent sends, and every post published to the
    Vote Uncovered page; include enough context to find the thread (parent post snippet or permalink if available).
  - Thread follow-up — When someone replies to the agent's comment, log each incoming reply (author display name and message text as returned by the API)
    and each agent response in turn, so the conversation under the agent's comment is reconstructible from the file alone.
  - Other actions — Record sync-elections outcomes (counts or file hash), intentional skips (no election, guardrail hit, already commented), and errors with
    enough detail to debug.

  `run.sh` may keep a separate `logs/run.log` for cron output and stack traces, but the action log is the human-first record of behaviour on Facebook.

  Log files should be gitignored (or only aggregated samples committed); on the VPS they persist with the repo for ongoing review.

  ---
  Guardrails (hard limits)

  - Never mention specific candidates or parties
  - Never comment on national-level politics (Westminster, devolved parliaments)
  - UK local elections only
  - Never tell people who to vote for — only why voting matters
  - Never engage with hostile or trolling replies beyond a single polite response
  - Never comment on the same post twice

  ---
  Facebook Graph API

  | Permission              | Purpose                                      |
  |-------------------------|----------------------------------------------|
  | pages_manage_posts      | Post to Vote Uncovered page                  |
  | pages_manage_engagement | Comment on other pages, reply to comments    |
  | pages_read_engagement   | Read posts and comments on monitored pages   |

  Auth: Long-lived Page Access Token for Vote Uncovered page, stored in .env

  ---
  Hosting: Hostinger VPS + OpenClaw

  What a Hostinger VPS + OpenClaw gives you

  - Runs the daily sync → monitor → post → reply pipeline on a cron schedule, 24/7
  - No dependency on your laptop being on
  - Claude API calls happen server-side
  - Logs persist in one place, including the append-only action audit (every agent action, comment text, and replies to the agent's comments — see Action log)
  - Easy to add more agents or projects later (you already have politech-awards and sugaroverflow running locally)

  What you need on the VPS

  | Component      | Detail                                              |
  |----------------|-----------------------------------------------------|
  | OpenClaw       | Installed and configured with your Claude API key |
  | This repo      | Cloned from GitHub                                  |
  | .env           | FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID                    |
  | Cron job       | 0 9 * * * /path/to/run.sh — runs daily at 9am       |
  | Python 3 + deps | For the scripts                                    |

  Hostinger VPS spec: their cheapest plan (KVM 1, ~£4/mo) would comfortably run this — it is all lightweight API calls, no heavy compute needed.

  One thing to sort first: the Facebook Developer App review. If you are making API calls from a server rather than interactively, you need a long-lived Page Access Token (valid 60 days, renewable) stored in .env on the VPS.

  Stack (confirmed)

  - Hostinger VPS — hosting + cron
  - GitHub repo — source of truth
  - OpenClaw — agent runtime
  - Claude API — the brain

  ---
  Project Structure

```text
voteuncovered-agent/
├── .claude/
│   └── agents/
│       ├── monitor-agent.md       # Watches pages, posts comments
│       ├── reply-agent.md         # Handles replies
│       └── post-agent.md          # Generates own-page content
├── scripts/
│   ├── monitor.py                 # Poll pages, comment on relevant posts
│   ├── reply.py                   # Check and respond to replies
│   ├── post.py                    # Post to own page
│   ├── sync_elections.py          # Fetch election data
│   ├── graph_api.py               # Facebook Graph API wrapper
│   ├── election_data.py           # wheredoivote / whocanivotefor fetchers
│   └── run.sh                     # Daily entrypoint: sync → monitor → post → reply
├── config/
│   └── pages.txt                  # Curated list of page IDs to monitor
├── data/
│   ├── elections.json             # Cached election data (gitignored)
│   └── commented.json             # Log of posts already commented on
├── logs/
│   ├── run.log                      # Cron / script stdout, errors (optional)
│   └── actions.log                  # Append-only audit: every action, full comment/reply text, thread responses
├── .env.example                   # FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
├── .gitignore
└── README.md
```

  ---
  Comment Examples

  ▎ "Did you know there's a local election coming up in your area? Your vote really does make a difference at the local level — from your bin collections to
  ▎  your local parks. Find out more at whocanivotefor.co.uk 🗳️"

  ▎ "Local elections are just around the corner! It only takes a few minutes to have your say on the issues that matter most in your community. Check if
  ▎ you're registered at gov.uk/register-to-vote 🗳️"

  ---
  Next Steps (deferred — revisit during testing)

  - Link out to voteuncovered.com or electoral commission in comments
  - Analytics/reporting on engagement and reach
  - Expanding to other social platforms
  - Discord notifications on daily run summary

  ---
  Open Questions

  - GitHub org/username for the repo (user to confirm)
  - Postcode/area coverage — derived from each page automatically

  ---