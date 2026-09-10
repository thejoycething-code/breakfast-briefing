---
name: parl-monitor-week-ahead-table
description: "Week ahead is a five-column table (option C, no score badge) since 7 Sept 2026; What's On items keyed on Parliament's Id; legacy rows backfilled; Bill links come from the board"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T04:16:16.676Z
---

Christopher chose option C for the Week ahead section on 2026-09-07: a table
(When · What · Where · Why it matters · Sources), keeping the judge's why-line
but with no 1/2/3 score badge. Rendered by `_event_rows`/`_event_table` in
src/digest.py; Further afield is the same table as a sub-block.

**Why:** before it, each line was the why-line alone with no time, venue,
petition, Bill or link, and every event printed twice. The duplicates came from
keying whatson items on `hash(label)` (per-process seed) so each Sunday that saw
an event stored it again. Items are now keyed `whatson:<date>:<Parliament Id>`
and the renderer folds duplicates by event_id anyway.

**How to apply:** structured fields (event_id, start/end time, house, type,
description, members, bill_id) live in the item's `extra`; rows stored before
7 Sept were filled by `tools/backfill_whatson.py` from data/raw What's On files
(pull → backfill → push store). What's On leaves BillId empty on Private Members'
Bills, so the Bill link falls back to the bills board by title. The week starts
at week_commencing: last Friday's business is not "ahead". A dry-run Monday
publish rebuilt the edition and deployed the partner site with the table.
See [[parl-monitor-build]], [[parl-monitor-store-artifact]].

**Hansard links (7 Sept, later that day):** the pull stores every Hansard section per sitting day in `hansard_sections` (`oral.day_sections`, both Houses) and `link_whatson_to_hansard` matches past What's On items (petition number, else title token overlap ≥0.5; unsure = no link) into `extra.hansard_url`; the renderer leads Sources with `[Hansard]`. Visible only on re-render, since Monday's rows are in the future. Re-run: `tools/pull_sources.py --only sections,links`.
