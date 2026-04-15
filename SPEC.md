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

  - Checks replies on Vote Uncovered's own comments daily
  - Responds in a helpful, cheery tone
  - Answers questions about where/when to vote using wheredoivote.co.uk
  - Stays on-topic: redirects off-topic replies gracefully

  3. post — Own Page Content

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
  Project Structure

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
  │   └── elections.json             # Cached election data (gitignored)
  │   └── commented.json             # Log of posts already commented on
  ├── logs/
  │   └── run.log
  ├── .env.example                   # FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
  ├── .gitignore
  └── README.md

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