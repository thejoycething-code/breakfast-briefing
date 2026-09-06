---
name: meta-organic-reports
description: "Organic FB/IG reporting pipeline at ~/Desktop/Claude Code Projects/Meta Reports — LIVE, 36 pages, 2,700 posts, MCP deployed; own Supabase project since 29 Aug 2026"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2168d5ed-2f28-4dd8-af26-046baad76925
  modified: 2026-08-29T18:55:34.298Z
---

Organic Facebook + Instagram reporting pipeline for CitizenGO Pages, started
19 Aug 2026. Lives at `~/Desktop/Claude Code Projects/Meta Reports`, private repo
`thejoycething-code/citizengo-meta-reports`. Node is at `~/.local/node/bin`, not
on PATH. Zero npm dependencies.

**State as of 29 Aug 2026:** live and collecting. 36 pages configured, **25
actively publishing** (11 published nothing in 90 days — dormant, not broken).
2,702 posts, 5,431 metric snapshots, ~90 days deep on 21 of 25 pages.
Instagram: 8 accounts, 696 media rows, **metrics still blocked** on
`instagram_manage_insights`.

**Supabase project `hxymihnuzbxianbpdovo` (eu-west-2) was renamed from "Clacton
By-election" to "CitizenGO Meta Reporting"** on 29 Aug 2026 — the Clacton campaign
closed 7 Aug and its Vercel app is down. Same project ref, URLs and keys.

**Hosted MCP:** `https://meta-organic-reporting.vercel.app/api/mcp`, 10 tools,
OAuth + static bearer tokens. See [[meta-mcp-security-posture]].

Runs unattended: nightly collection 04:30 UTC, weekly digest Mondays 06:00,
watchdog 09:00 daily, heartbeat 1st & 15th (GitHub disables cron after 60 days of
repo inactivity — the heartbeat exists solely to prevent that).

**Why the probe mattered:** Meta retired the `post_impressions*` metric *names*
but the data survived via breakdowns — `post_media_view` + `breakdown=is_from_ads`
gives the organic/paid split, `is_from_followers` gives follower reach,
`post_total_media_view_unique` gives unique reach. Never reason from Meta's
deprecation docs; probe live.

**How to apply:** never batch insights metrics (one invalid metric fails the whole
call). Never put a gated field in a `published_posts` field list (one bad field
returns #10 and loses every post). Page-scoped edges reject user tokens — exchange
for a Page token via `/me/accounts?fields=access_token`. #100 is overloaded
("retired metric" AND "object does not exist") — classify on message text.
#200 on `post_total_media_view_unique` means "suppressed on this low-follower
page", not failure.

**Access runs through Ignacio's personal Facebook profile and will for now.** A
System User must live in a Business Portfolio, and the **citizenGO portfolio
(731536880628289) cannot have apps added to it** — that portfolio owns 11 pages
carrying **86.7% of all views** (HazteOir alone 65.5%), so there is no useful
subset to migrate around it.

The token does **not** expire — verified 29 Aug 2026, `expires: never`. What
expires is Meta's **data access window: 90 days, ending 24 Nov 2026**. Past that
the token still authenticates and returns EMPTY results rather than an error.
Renewal = the profile owner re-authorises the app, which resets the window.
`scripts/check-token-expiry.js` runs in the watchdog daily, warns at 21 days,
fails at 7, and asserts scopes (a token renewed without `read_insights` returns
200 with an empty body). Add `instagram_manage_insights` during that
re-authorisation — it is the same action and unblocks Instagram metrics.

**DEFERRED by the user on 29 Aug 2026 — do not raise again unless asked:** rotating
the exposed legacy JWT secret, and per-person MCP tokens. Both were explained and
declined. The shared read-only token is an accepted trade-off, as it was in August.

Comment *counts* are collected; comment *text* deliberately is not, on GDPR
grounds. Revisit only as a deliberate decision — it would enable sentiment
analysis and supporter response.

See [[meta-page-portfolio-map]], [[meta-system-user-setup]],
[[meta-silent-failure-pattern]], [[meta-mcp-security-posture]].
