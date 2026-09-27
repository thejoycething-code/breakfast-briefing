---
name: parl-monitor-answer-kind
description: answer_kind — the judge label the questions section ROUTES on; rules outrank the judge, only rule-detected positions may lead, and the bank counts wrongly-demoted apart from plain disagreement
metadata:
  type: project
---

`items.answer_kind` (figures | position | restated) is what the Westminster
questions section routes on, added 25 September 2026 when Christopher asked
for "those two as a judge field" and said the section still took too much
space.

**Why:** the body was 82% of the section's bytes. Routing "restated" to the
tail took the section 23.7KB → 15.1KB and the edition 27.8KB → 22.9KB.
Removing unanswered questions — the other half of the same request — bought
1.5%, because the sweep only ever fetches `answered=Answered`.

**How to apply:**

- **Rules outrank the judge.** `digest.ANSWER_RULES` detects REFERRED /
  NOT HELD / DEFERRED / POSITION from formulaic phrasing; only when none
  fires does `JUDGED_LABELS` consult `answer_kind`. An unknown label is
  discarded and an unjudged row keeps none — it stays in the body, which is
  the safe direction.
- **Only a RULE-detected position may lead the section.** The judge's
  "position" has no sentence to point at, and the first run's fallback
  bolted the opening 40 words into a quotation with a department's name
  against it, printing the same child-safety boilerplate twice. A lead with
  no identifiable sentence is not a lead. `_label_and_source` exists solely
  to keep that distinction.
- **The judge could not see the answer, and still cannot see much.**
  `EVIDENCE_KEYS` carried neither `question_text` nor `answer_text` until
  this change, so a written question was scored from its HEADING alone.
  `items.extra` never stored the answer either — only `data/raw` had it.
  `tools/judge_answers.py` backfills extra from the archive (free, local).
- **The bank measures the two error directions apart.** `evalbank.kind_stats`
  counts `wrongly_demoted` (judge=restated, human≠) separately from
  `wrongly_kept`, because a wrong label HIDES an answer rather than
  misplacing it. The sample prints the question and reply above the KIND
  line; without them a reviewer is guessing.
- **`judge_answers.py --bank-existing`** banks labels already in the store
  with no API calls. Bank under the EDITION week, not today: the window is
  [Monday-7, Monday), so 15 Sept belongs to the 21 Sept edition.
- **`tools/judge_eval.py` is in NO workflow** — the sample and report happen
  only when someone runs them.

Related: [[parl-monitor-pq-answers-in-edition]], [[parl-monitor-judge-eval]],
[[parl-monitor-edition-recess-shape]].
