---
name: parl-monitor-deferred
description: Parl-monitor features Christopher deferred and asked to be reminded about
metadata: 
  node_type: memory
  type: project
  originSessionId: 2fa51e3b-34ec-4638-9e48-df2232ac2520
  modified: 2026-08-26T00:04:21.070Z
---

Things Christopher explicitly parked on the Parliamentary Monitor. **Raise these
when he next asks what to build**, rather than waiting for him to remember.

**Cross-issue matrix page (he asked to be reminded, 2026-08-06).** He liked
mockup C in docs/5ca-sheet-mockups.html: one row per member, one column per
campaign area, showing their placement in each. His refinements: build it as a
**separate page**, not inside the 5CA sheet, and **include a total across all
issues**. The case for it is Naz Shah, a strong ally on assisted dying and
against us on abortion and free speech, which no single-area sheet reveals.

**Confidence markers.** A strong/moderate/thin marker per placement, derived
from the evidence hierarchy, so a placement resting on four neutral questions
does not read as firmly as one resting on a division. He said "suggest later".

**Peers.** The 5CA covers 649 MPs and no peers, while the ledger holds 132
Lords divisions, 47,130 peer votes, 5,283 Lords speeches and 902 peers with
evidence. The Terminally Ill Adults Bill died in the Lords, so this is the
chamber that actually beat us. He said "a decision for later".

**Daily alerts (run_alerts.py) — rejected for now**, not deferred: "no daily
editions yet". Do not re-propose until the weekly rhythm is established.

**Vote-card layout — BUILT 2026-08-26 (option B, the bill's passage).** The
card is now chronological: Second Reading, committee quotes, Report Stage
amendments, Third Reading, with the headline verdict kept in the header so
it is not buried. Option D (compact roll) was deliberately NOT built — the
largest card any member can have is seven votes, so the threshold would be
dead code. Don't re-propose it unless the tracked-division count grows a
lot.

**Undeployed as of 2026-08-26.** Several rounds of work are committed and
pushed but the live site still serves the Monday publish #14 build: the
"Also on the record" receipts, the shareable-quote rewrite, real service
history, the per-party whip rule, the "Various" heading fix and the
passage cards. A `Monday publish` with dry_run ticked deploys them;
otherwise Monday's scheduled run does. Don't assume the public page
matches the repo.

Related: [[parl-monitor-build]], [[api-spend-approval]].
