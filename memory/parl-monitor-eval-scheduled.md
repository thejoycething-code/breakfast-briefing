---
name: parl-monitor-eval-scheduled
description: The judge evaluation runs in the Monday publish and the German weekly since 25 Sept 2026 — ingest before sample before report, before the store push; the German loop had been write-only
metadata:
  type: project
---

Both judge-evaluation loops are scheduled since 25 September 2026
(Christopher: "wire judge_eval into the monday publish", then "do the same
for the german one"). Before that neither was in any workflow: the sample
was written and `docs/judge-eval.md` regenerated only when someone
remembered.

**Why it matters now:** the Westminster edition ROUTES on the judge's
`answer_kind` ([[parl-monitor-answer-kind]]), so drift there hides real
answers rather than misplacing them.

**How to apply:**

- **Order is asserted by tests, not convention:** `ingest` → `sample` →
  `report --write`, and the whole step BEFORE `db_state.py --push`, because
  ingest writes human verdicts into the store.
- **Westminster** runs it in `monday-publish.yml`. Verdicts are banked by
  the SUNDAY PULL, where triage runs — not by the publish. Monday is right
  anyway: it is the first moment the edition exists to be checked against,
  and a Sunday sample would race the pull that writes what it samples.
- **Germany** runs it in `de-weekly.yml`, AFTER the triage step, because
  Germany pulls and publishes in one workflow.
- **The German loop was WRITE-ONLY.** `ingest_samples` matched only
  `judge-sample-*`, so `de-judge-sample-<week>.md` was never read and a
  filled German checklist would have vanished silently. `evalbank.SAMPLE_FILE`
  now matches both. The German tool had no `ingest` command at all.
- **`sample` refuses to overwrite a checklist with verdicts in it.** Harmless
  when a human ran it; run weekly, a second run in the same week would blank
  a reviewer's work.
- **`rescore` is deliberately NOT scheduled** (a test says so): every other
  action reads the store, rescore spends.
- Both tools write the same `docs/judge-eval.md`; the report is
  jurisdiction-split, so either regenerating it is correct.
- KIND guidance is appended to a sample only when it contains a KIND line —
  a German checklist is all Vorgänge and never a written question.

Related: [[parl-monitor-judge-eval]], [[parl-monitor-answer-kind]],
[[parl-monitor-germany]].
