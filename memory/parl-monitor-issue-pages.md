---
name: parl-monitor-issue-pages
description: "Issue pages (7 Sept 2026): partner_site/issues.html + issue-<slug>.html per area from src/issuepages.py; six-month window; bills_board areas are CSV not JSON; migration has no page"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T17:32:04.965Z
---

Christopher, 2026-09-07: "Build the issue pages." One page per campaign area on
the partner site, built by run_monday (`issuepages.build`) after the petitions
page, committed with the companion pages, linked from the nav as "Issue pages".

**Content per page** (`issuepages.collect`, read only, window 183 days; activity
by month for 365): Bills on the board (bills_board, status live), the editions'
items score ≥2 with why-lines, activity by month (questions / speeches / motions /
votes from mp_events), debates grouped by RawHansard debate_id with with/against/
neutral/unscored counts from `stance`, divisions grouped by ref base with ledger
lobby counts (not the official tally; says so), sponsored EDMs, most recent 40
questions (pq_link URLs), petitions from `petitions` + `dv_petitions`. Migration
(11) has no page. No member placements: that is the 5CA's job.

**Traps:** `bills_board.areas` is a comma-separated string ("2,6"); the ledger's
`areas` is a JSON list — `_areas()` accepts both (first build showed zero Bills
everywhere). `stance` is not in db.SCHEMA; `collect` calls `stance.ensure_table`.
Items table is the weekly working set (~73 rows), so most page content comes
from the ledger, not items. Generation takes ~2s for 12 pages (RawHansard load).
See [[parl-monitor-petitions]], [[parl-monitor-week-ahead-table]].
