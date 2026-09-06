---
name: parl-monitor-devolved-judge
description: Devolved triage runs in the Monday publish (not the secret-less weeklies), fenced by an 8-min budget; devolved_triage reads config/secrets.yaml so unsetting the env var does NOT make it safe
metadata:
  type: project
---

**Decision (Christopher, 6 Sept 2026):** the devolved judge
(`tools/devolved_triage.py`) runs inside the **Monday publish**, before the
edition renders — NOT in `sp/sd/ni-weekly`, which carry no secrets by design
(the structural rule that keeps Slack tokens out of the watching briefs; a
test pins that they still carry none).

**Why fenced:** Monday has 30 minutes for everything; the first devolved pass
was 315 items (~79 calls). `triage.score_in_slices(budget_seconds=…)` stops
starting slices after 8 minutes and reports the leftover; scores are
once-ever so the leftover is simply next week's work. A subprocess timeout
(660 s) sits outside it.

**Before this, the state was misread:** Westminster and EU triage were already
running weekly; only the devolved judge had never been wired. "Un-pause
triage" really meant "wire it for the first time". The 4 Sept local run (538
items) was never published and is gone.

**Trap, paid for:** `devolved_triage.py` (and `eu_triage.py`) fall back to
`config/secrets.yaml` when `ANTHROPIC_API_KEY` is unset. `env -u
ANTHROPIC_API_KEY python3 tools/devolved_triage.py` is NOT a dry run — it
runs live. To size the backlog without spending, import the module and call
`pending()` (0.1 s), never `main()`. On this laptop the live path sat ten
minutes and spent nothing — every call failed — which is what the budget is
for.

Related: [[parl-monitor-store-guard]], [[parl-monitor-welsh-verdicts]].
