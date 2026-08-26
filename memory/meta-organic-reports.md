---
name: meta-organic-reports
description: "Organic FB/IG post pipeline at ~/Desktop/Claude Code Projects/Meta Reports — Phase 0 probe DONE 20 Aug 2026, reach/organic-split survive, page inventory is the real blocker"
metadata: 
  node_type: memory
  type: project
  originSessionId: d5b2f9af-42d5-42a3-8721-87548aa3839f
  modified: 2026-08-20T07:49:19.151Z
---

Organic Facebook + Instagram post data pipeline for CitizenGO Pages, started
19 Aug 2026. Lives at `~/Desktop/Claude Code Projects/Meta Reports`; plan at
`~/.claude/plans/can-you-scope-out-federated-moon.md`. Reuses the
[[clacton-vercel-deployment]] stack. Node is at `~/.local/node/bin`, not on PATH.
**LIVE AND COLLECTING as of 20 Aug 2026.** Private repo thejoycething-code/citizengo-meta-reports;
nightly GitHub Actions run writes to the **Clacton By-election** Supabase project
(hxymihnuzbxianbpdovo, eu-west-2) where the meta_* tables sit beside clacton_actions.
**BLOCKED 25 Aug 2026** on admin rights to the citizenGO portfolio (731536880628289).
Plan agreed: re-home the System User OFF Joyce.Digital (the user's PERSONAL portfolio,
which currently holds the only working token) and onto citizenGO, which already owns 11
of the 22 pages. Other portfolios then partner-share their Pages into that hub — share,
never move. Re-homing loses no data: everything is keyed on page_id, tokens are only
access. Expect UK to drop out of collection until Joyce.Digital shares it back in.
See [[meta-page-portfolio-map]].
Running unattended: nightly collection 04:30 UTC, weekly digest Mondays 06:00 UTC.
Holds 123 posts / 90 days for **Citizen GO UK only** — that System User reaches 1 page.
Baseline: median 4,716 views, 19.5 shares, 83% beyond followers; best post 833k views.
A 365-day backfill is deferred until more pages are available (do it once, not twice).
**Watch: GitHub disables cron after 60 days of repo inactivity — ~19 Oct 2026 both
workflows stop silently, and since both are cron neither can warn about the other.**

**Why:** the probe overturned the scoping assumptions, so don't reason from the
deprecation headlines. Meta retired the `post_impressions*` metric *names* (all
seven confirmed dead, plus `page_impressions` and `page_fans`) but **the data
survived via breakdowns**: `post_media_view` + `breakdown=is_from_ads` still gives
the organic/paid split, `breakdown=is_from_followers` gives follower reach, and
`post_total_media_view_unique` still gives unique reach. So engagement comes from
the **`/insights` edge**, which is *less* permission-gated than the post object —
the post's `reactions`/`comments` connection fields need
`pages_read_user_content`, while `post_reactions_by_type_total` does not.

**How to apply:** never batch insights metrics — one invalid metric fails the whole
call, so probe and collect one at a time. Never put a gated field in a
`published_posts` field list; one bad field returns #10 and loses every post.
Page-scoped edges reject user tokens outright (#210/#190) — you must exchange for a
Page token via `/me/accounts?fields=access_token`, and a System User token alone is
not sufficient. Treat #200 on `post_total_media_view_unique` as "unavailable for
this page" (suppressed on low-follower pages), not a failure. #100 is overloaded —
it means both "retired metric" and "object does not exist", so classify on the
message text, not the code.

**The real blocker is inventory, not metrics:** the ads API listed 35 pages but
`/me/accounts` returns only **3** readable ones (Citizen GO Scotland, CGO Sandbox,
CitizenGO main at 117k followers). Ads permission is not read permission, and the
pages sit across 12+ Business Managers with no common owner — hence a per-page
token registry, not one global token. Same live-probe-before-schema discipline as
[[parl-monitor-build]]; comment text stays deferred (see the plan's future
possibilities).
