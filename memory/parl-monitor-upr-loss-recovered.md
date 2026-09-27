---
name: parl-monitor-upr-loss-recovered
description: The 3 Sept 2026 UPR clobber was recovered on 25 Sept by re-running pull_upr; the guard never failed, the recovery was simply never done, and a committed artefact is what made the loss provable
metadata:
  type: project
---

The coverage watch failed every day from 21 September 2026 reporting
`upr_recommendations last saw data 40 days ago`, and nobody read it. It was
correct. Recovered 25 September: 2,331 → 4,336 rows.

**What it was:** the aftermath of the incident `tools/db_state.py`
`check_lineage` documents — on 3 Sept the UPR monthly harvested 1,218 new
recommendations, published them, and a hand push from a laptop with an older
store overwrote them three hours later. The lineage guard and the coverage
watch were written the NEXT DAY in response (`ee8be3ac`).

**How to apply:**

- **Nothing got past the guard.** The loss predates it by a day. The guard
  works — it refused a push of mine on 25 Sept. Do not go looking for a
  vulnerability; look for the *recovery* that was never done.
- **An alert nobody reads is not a control.** This one fired for three weeks.
  When investigating "what next", read the failing watches first.
- **`pull_upr.py` re-derives from the UPR Info database**, so a clobbered
  harvest is recoverable by re-running it, not lost. Regenerate
  `docs/upr-tracker.md` afterwards — it was AHEAD of the store (3,552 vs
  2,331), and anything regenerating it from the store would silently write
  the short count.
- **The committed artefact is what made it provable.** Per-table row counts
  only entered the sidecar on 10 Sept (`3aaa31e0`), already showing 2,331, so
  there is NO row-count history across the event. The proof came from
  `docs/upr-tracker.md` being committed by CI. A table with no committed
  artefact beside it would have gone quiet unnoticed.

Related: [[parl-monitor-store-guard]], [[parl-monitor-store-divergence]].
