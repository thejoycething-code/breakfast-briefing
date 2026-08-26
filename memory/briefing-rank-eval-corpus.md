---
name: briefing-rank-eval-corpus
description: "archive_day.py banks each edition's labels; rank_eval.py scores importance() against them — but concordance measures agreement, not correctness"
metadata: 
  node_type: memory
  type: project
  originSessionId: 56a31411-1c43-4503-ab50-1e5a9db75951
  modified: 2026-08-18T22:59:48.253Z
---

Each edition is archived by `archive_day.py` (Step 8 of the brief, straight after
`mark_published.py`) into `archive/YYYYMMDD/`: gzipped sweep, picks, composed.json, manifest.
~320KB/day, ~115MB/year. `rank_eval.py` replays the current `importance()` over every archived
edition and reports concordance (pairwise agreement with the tier labels), top-40 precision and
tier-1 recall; `rank_eval_log.txt` keeps the history. Baseline 18.08.2026: **concordance 0.607,
top-40 0.57** on one flat (untiered) edition.

Labels: tier 1→3, tier 2→2, tier 3→1, unpicked→0. A pick cut by a section cap keeps its tier —
the cap is a volume constraint, not a verdict. Flat pre-tier picks all score 2, a blunt
two-level signal; tiered days are much sharper.

**The critical caveat, found the hour it was built:** replaying the three substring bugs fixed
that day back into the scorer *improved* concordance (bare `freed` matching "freedom" scored
+0.0031). The bug was a good predictor because religious freedom is a core beat and its stories
get picked. So **concordance measures agreement with Chris's revealed preference, not
correctness** — a spurious feature correlating with a favoured beat scores well.
`testcases.txt` therefore holds veto power over rank_eval, never the reverse: use ABOVE pairs
for axioms, rank_eval only to choose between changes that are already defensible.

Also don't read 0.607 as a grade. Random scores 0.500; picks are made using article text,
provenance, geographic balance and cross-section judgement that `importance()` doesn't model —
it is a reading-order heuristic, not a curator. The measurement is exact (same corpus, same
labels), so any difference between two scorers on one day is real; what one day cannot show is
whether it generalises — day structure alone moves the number ~0.05.

Validated with controls: perfect scorer 1.000, inverted 0.000, random 0.500 (sd 0.027 over 12
seeds). `run_tests.py` smoke-tests the archive→eval round trip in a temp dir, because a broken
`archive_day` loses labels silently while the edition still publishes. Both scripts take
`--archive-dir`. Related: [[briefing-markup-becomes-testcase]],
[[briefing-cap-drops-get-marked]], [[briefing-text-for-judgement-only]].
