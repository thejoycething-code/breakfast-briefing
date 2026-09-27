---
name: parl-monitor-eu-monitor
description: EU Parliament monitor brought to parity with Westminster 17-18 Sept 2026 -- per-sitting-day sweep, body-matched texts, once-ever triage, and the same-night API quirks that bit the first live run
metadata:
  type: project
---

The EU side of parl-monitor was dead for eleven days (rows emptied by the 9 Sept
rebuild, runs cancelled not failed, watch printed NO DATA and moved on) and was
rebuilt 17 Sept 2026: `.github/workflows/eu-day-sweep.yml` (23:00 UTC) runs
`tools/eu_day_sweep.py` per sitting day; `tools/eu_texts.py read_bodies` matches
adopted texts on the .docx body via `src/eudoc.py` (took texts on our ground
8 -> 44 of 145); `tools/eu_triage.py` scored all 309 matched rows once, ever.
EU channel posting stays on hold: DM only.

**Why (what the first live sweep, 18 Sept, taught):**
- The night a sitting ends, EP Open Data carries a voted item's label in `fr` and
  in `mul` ("fr - en - de" joined by " - ") but NOT yet under `en`. The pull took
  `en` only and skipped all ten of 17 Sept's items, then DM'd "0 divisions".
  `eu_rollcalls.english_label()` lifts the English segment from `mul` (stopword
  score) and `heal_labels()` refreshes the prefix once `en` arrives, because the
  `known` skip would otherwise freeze the night's label for ever.
- `config/secrets.yaml` is absent on Actions; three tools had grown private
  env fallbacks and the fourth caller did not. The fallback now lives in
  `publish.load_secrets()` itself (`ENV_SECRETS`).
- Divisions are matched on their subject LABEL only; adopted texts on their body.
  On 16 Sept the gender-inequalities-in-health resolution matched 14 terms
  (abortion, SRHR, transgender) as a text, while its 98 roll calls were never
  stored. Open decision: let a division inherit its adopted text's areas.
- Inheritance multiplies: one text lends its ground to up to 139 roll calls. The
  first cut (18 Sept, morning) ignored the text's verdict and queued 587
  amendment votes for the judge, 65 of them under a Ukraine report scored 0. A
  division now inherits only from a text scored 2+ or not yet judged, records
  `inherited_from`, and takes the TEXT's score via `eu_triage.propagate()`; it is
  never judged on its own. `src/eugate.py` is the one bar (score 2+ or unscored)
  for the edition, the MEP tracker and the meaning-line queue.
- Split-vote texts live on the vote item (`was_motivated_by` SPLIT ->
  `expressionContent`), free with the fetch; labels read "§ 85/2: the words
  ‘and rights’". Amendments key as "Am 51" (decision) not "Amendment 51" (split).
- Reports (A-) and motions (B-) sit on different distribution shelves from
  adopted texts (`eudoc.SHELVES`); a rejected paragraph is only in the report.
- Only matched divisions are stored, so "0 rows for a sitting" is not by itself
  a fault: check the API's PLENARY_VOTE_RESULTS count for the meeting id first.

**How to apply:** when a same-night collector reads a multilingual EP field,
never require `en`; when a new column or a new tool needs credentials, call
`publish.load_secrets()` and nothing else; treat a text/division mismatch on the
same title as the label-vs-body gap, not as a taxonomy miss. Related:
[[parl-monitor-store-guard]], [[parl-monitor-taxonomy-v16-areas]].

**Queue metric and the judge's frame (20 Sept 2026).** `meaning_line_queue.european()`
ranks unsigned divisions by how many MEPs a sign-off would move between 5CA
bands (`band()` mirrors `make_eu_5ca`), on the side CONSISTENT with existing
placements; the other side's count is the coalition being shredded, and the
contradictions on the consistent side are printed so cross-cutting votes show
as such. The EU judge has its own frame (`triage.SYSTEM_PROMPT_EU`): under the
Westminster prompt it scored EU items by UK effect ("no direct UK policy
trigger"); rescoring the UK-framed zeros and score-1 rows lifted 21 to the
digest bar, the Cyprus rape-survivors SRHR text to 3. Amendment documents
(B-…-AM-n) are NOT in Open Data and doceo bot-walls them: read an amendment
from the split definitions on the vote item, or from the adopted text minus
the motion.
