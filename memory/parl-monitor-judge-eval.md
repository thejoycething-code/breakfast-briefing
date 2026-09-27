---
name: parl-monitor-judge-eval
description: "Judge evaluation corpus (7 Sept 2026): judge_verdicts bank + data/eval/<week>.jsonl, ten-item sample checklist reviews/judge-sample-<week>.md, docs/judge-eval.md agreement report, guarded rescore for drift"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T13:34:19.860Z
---

Christopher, 2026-09-07: "Build the judge evaluation corpus." Modelled on the
briefing project's label banking ([[briefing-rank-eval-corpus]]).

**Shape.** `src/evalbank.py`: `bank()` after every judge pass in run_weekly (what the
judge saw: title/tier/candidate areas; what it said: score/why; model, prompt sha,
mode live|stub|historic) → table `judge_verdicts` (PK week+item_id, sighting column
`captured_at`), `export()` → `data/eval/<week>.jsonl` committed. run_monday:
`ingest_samples()` (VERDICT lines in reviews/judge-sample-*.md = explicit truth;
PRIORITY ACT/WATCH/NOTE in review-*.md = implicit 3/2/1, never overrides explicit),
`write_sample()` (10, stratified ≥2 per score present, seeded by week),
`report()` → docs/judge-eval.md (exact, within-one, over/under, confusion matrix,
digest precision/recall for score≥2, by month, by feed, notes, prompt/model versions).
CLI `tools/judge_eval.py sample|ingest|report --write|export|seed|rescore [--spend]`.
`rescore` re-runs the current judge over labelled items and compares then/now/human;
spends money, refuses without `--spend`.

**Why:** nothing recorded verdicts beyond the current store row; a prompt or model
change could not be measured. Note the items table holds only the weekly working set
(73 rows on 7 Sept), so the bank is the only history.

**How to apply:** the human verdict is truth, the judge is measured; concordance is
agreement not correctness. Historic seed = 70 verdicts (mode historic) keyed to the
edition Monday after capture; the sample may draw from any non-stub mode. First
sample: reviews/judge-sample-2026-09-07.md awaits Christopher's VERDICT lines.
