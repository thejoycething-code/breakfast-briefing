---
name: briefing-clustering-two-purposes
description: same_story and corroborate cluster for different purposes and must stay different; entity links are token-level with a 3-word co-occurrence floor
metadata: 
  node_type: memory
  type: project
  originSessionId: 56a31411-1c43-4503-ab50-1e5a9db75951
  modified: 2026-08-18T23:40:48.497Z
---

There are two clustering paths in `shortlist.py` and **they must not be unified**, despite
looking like duplication:

- `corroborate()` answers "how big is this event?" → deliberately **global, cross-section**,
  because a big story crosses sections (its docstring: the Trump Medicaid ruling landed in
  Life, Gender and Church at once, and counting inside one section scored it as three small
  stories). Feeds `_corr` → `importance()`, and picks the sheet's one-line-per-story lead.
- `same_story()` answers "is this the same article to read?" → **never merges across
  sections**, so the free-speech angle of a story gets its own sheet line (Chris, 17.08.2026).
  Feeds `cluster_duplicates()` and the advisory "(same story as N - prefer that)" flags.

**Fixed 19.08.2026.** Entity links were exact-string on PHRASES, since `entities()` returns
runs of up to three capitalised words. "Susie Wiles Impersonator" never matched "Wiles", and
"Philippine" never matched "Philippines", so genuine duplicates ran as separate leads.
`ent_tokens()` now yields normalised single tokens (≥5 chars, light plural fold on >6), and the
DF gate works better on tokens: a rare phrase built from common words used to pass as
distinctive, while a common token now fails on its own frequency.

Also `ENTITY_COOCCUR_MIN = 3`: a shared rare entity plus **three** other significant words,
not one. Measured against 18.08's picks, wrong flags (Chris kept the flagged item, rejected its
lead) fell **32 → 13** and precision 32% → 22% wrong, flags 219 → 119. Four Indonesia quake
reports had been flagged as duplicates of a Dearborn unity rally on the token "christian" alone.
The residual 13 are a milder failure — mostly correct merges where his pick differed from the
chosen lead, i.e. lead selection, not false merging.

**Why precision over net:** the two errors are asymmetric. A wrong flag says "prefer that"
about a story he wanted and risks losing it; a missing flag costs one extra near-duplicate line
to read. Net (correct − wrong) is actually *highest* at the loose baseline, so optimising net
would have kept the bug.

**Measured and deliberately NOT applied:** routing `corroborate()` through `same_story()` gives
concordance +0.0014 and merges 29 more items. Rejected for now on two grounds — it would impose
same_story's cross-section ban on a function that is global by design, and +0.0014 on a single
archived day is exactly what [[briefing-rank-eval-corpus]] says cannot be trusted to
generalise. Revisit when several tiered days exist.

New fixture kinds `SAMESTORY` / `NOCLUSTER` encode both directions (two-item corpus so the
shared token clears `ENTITY_MIN_DF=2`). Also fixed: `cluster_duplicates()` crashed with
KeyError `_i` for any caller other than `main()` — same shape as the `--sheet` break the day
before. Related: [[briefing-cluster-provenance]], [[briefing-markup-becomes-testcase]].
