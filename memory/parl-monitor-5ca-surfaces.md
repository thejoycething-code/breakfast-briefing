---
name: parl-monitor-5ca-surfaces
description: Two sign-off surfaces (stance files vs votes files); devolved 5CAs wired 5 Sept; data/5ca grows in git and is now pruned
metadata:
  type: project
---

**Two sign-off surfaces, easily confused:**
- `config/{sp,sd,ni}_stance.yaml` — a human confirms what an aye MEANT on one
  named act. Drives the **5CA sheets**. Scotland 27 confirmed, Wales 5, NI 4.
- `config/{holyrood,senedd,nia}_votes.yaml` — `signed_off` publishes a VERDICT
  to every member page. Drives the **tracker pages**. Wales and NI still
  unsigned.

So a nation can have 5CA placements while its tracker says nothing about
meaning. That is not an inconsistency.

**Wired 5 Sept 2026** (`tools/devolved_5ca.py`, in each nation's weekly plus
run_monday): Scotland 5 sheets, Wales 1, NI 2. A sheet is kept only where a
member is placed at ++/+/-/--. Two traps when reading a 5CA CSV: every sheet
ends with a `Totals - N decision-makers` row whose empty columns hold the
STRING "0", and the neutral `0` column is not a placement.

**data/5ca grows in git** — `make_5ca.py` writes a DATED sheet per area per
run; it reached 109 files / 47MB, ~11 files a week, the shape of the problem
that forced the store out of the repo at 88MB. `tools/prune_5ca.py` now runs
in the Monday publish (keeps newest set, oldest baseline, last set of each
earlier month) and frees ~31MB. The devolved sheets use STABLE filenames so
they never accumulate. A dry run (`NO_PUBLISH=1`) prunes nothing.

Related: [[parl-monitor-store-guard]], [[parl-monitor-devolved-identity]].
