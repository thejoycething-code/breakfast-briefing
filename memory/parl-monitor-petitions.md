---
name: parl-monitor-petitions
description: "E-petitions early warning built 7 Sept 2026: weekly sweep of every open petition, snapshot table for movement, edition section with the 10k/100k ladder; the gate is tier 1 or watchlist, tier 2 only past 10,000"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T10:20:16.562Z
---

Christopher, 2026-09-07: "Build the e-petitions early warning." Both of the
day's Westminster Hall debates came from petitions crossing 100,000.

**Decision, same day:** "I'd like petitions not to be included in the weekly report." So petitions live in their own `petitions` table (never `items`, never judged, never rendered); `render_petitions` and the section were removed. They surface on the partner site's companion page `partner_site/petitions.html` (`partner.build_petitions_page`, built by run_monday next to the questions page, linked from the nav as "E-petitions on our ground"): fastest movers first, then every petition with signatures, movement since last sweep, ladder stage, areas, first seen. Public record only, no judge. First deployed 2026-09-07 via Deploy tracker.

**What exists.** `src/ingest/petitions.py` (API pages 25, ~91 open pages, ordered
by signatures, `links.next`; states open / awaiting_response / awaiting_debate;
listing pages NOT archived). `run_weekly.sweep_petitions` runs in the Sunday
pull after EDMs; `tools/pull_petitions.py` runs it standalone (pull → sweep →
push). Items feed `petition` with event_date = the Sunday seen (window 7 days),
extra carries signatures, prev_signatures, milestone, thresholds. Table
`petition_snapshots(petition_id, captured_at, signatures)` gives the "this
week" movement; coverage watches `captured_at` (the sighting-column naming
rule: `seen` fails test_coverage). Section "E-petitions on our ground" after
Early day motions (renamed from "EDMs and petitions"); a threshold crossed or
a debate date fixed in the week is a tag-3 top line. Area-11-only petitions
are stored and judged but not shown.

**Why the gate is shaped as it is:** the first sweep admitted 269 of 2,279;
168 came in on tier-2 words alone ("birth rate" in a student-loan petition,
"coercion" about China, "Ofcom" about broadcasting). Tier 1 or watchlist only
then dropped the misogyny hate-crime petition (114,927, debated that day),
whose only match is tier-2 "hate crime". Final rule: tier 1 or watchlist, or
tier 2 once signatures ≥ 10,000. Result 115 stored (31 migration-only).

**How to apply:** first snapshot taken 2026-09-07 so Edition 7 (14 Sept) shows
movement; items are judged by the Sunday pull (~115 extra items, pennies). The
tracker roll fix landed alongside: a question's quote now counts in ranking
and must pass `quotes.usable` (see [[parl-monitor-division-brief-and-spoke]]).
