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

**DEPLOYED 2026-08-26**, twice: Monday publish #15 (run 32955323692) and
again as run 32976100327, both with dry_run so no Slack post and no new
edition row. Live now: the receipts, shareable quotes, real service
history, the per-party whip rule, the "Various" fix, the passage cards, and
the profile hero (post line, majority, committee pills, contact as the
right-hand column with icon links).

**Verify a deploy from the run's own committed page, not by curling the
URL.** The partner site returns HTTP 401 to an unauthenticated fetch --
that is Vercel deployment protection working. And there is still NO GitHub
Pages config on this repo and nothing in monday-publish that deploys
`docs/`, so how the public passwordless page is served remains unknown --
ask before assuming it updated. `docs/` is committed and byte-identical to
the partner build.

**Reference data lives in member-profiles.yml (Wednesdays), never in
sunday-pull.** Its steps are guarded `if: env.SKIP != '1'`, which does not
run after a failure, so an enrichment step ahead of the weekly gather would
block the gather outright; and its 60-minute budget already covers a cold
pull measured at 40m05s. tools/pull_service.py and tools/pull_profiles.py
both run there. Tests pin this.

**`gh` is authenticated locally**, so `python3 tools/db_state.py --push`
works from the laptop without a PAT -- db_state falls through to the gh
branch when token() returns None. Useful when a workflow publishes a store
but its sidecar commit fails: the pull guard then refuses the divergence,
and a local push rewrites a matching sidecar.

Related: [[parl-monitor-build]], [[api-spend-approval]].
