---
name: briefing-suppression-two-buckets
description: "Briefing suppression has two causes — chaff is tiny, \"no section matched\" is where real news dies"
metadata: 
  node_type: memory
  type: project
  originSessionId: 94c9330d-09f8-49b5-9d3c-ddff9199b4fc
  modified: 2026-08-15T10:19:03.563Z
---

In the Breakfast Briefing shortlist, an item disappears for one of two unrelated reasons, and they
are now printed as separate blocks (`CHAFF` and `NO SECTION MATCHED`).

**Why:** on the 14.08.2026 sweep the single "SUPPRESSED (208)" list looked like a chaff problem. It
was not — only **20** were chaff; the other **188** simply matched no section. Chris asked me to
"fix the chaff rules" after a Zelensky/Patriot-missiles story vanished, and my diagnosis that an NFL
"Patriots" rule ate it was **wrong**: `is_chaff()` never fired on it. It, the Farage by-election
commentary, the A-level results and an anti-conversion-law story were all killed by
`classify()` returning `None`. The two need opposite fixes — tighten `CHAFF`, widen `OTHER_ALLOW` —
so one combined list sent every reader at the wrong one.

**How to apply:** always check *which* block an item fell into before proposing a fix. Chaff
over-matching is real but small ("slams", 13.08). The volume problem is `OTHER_ALLOW`, whose
misses are mostly stems and plurals rather than missing concepts — `law\b` never matched "laws",
`bill\b` never matched "bills", `university` never matched "universities", `reform uk` never
matched "Reform". Those four fixes alone rescued 20 items. When auditing, test the exact headline
against `is_chaff()` and `classify()` rather than reading the regex.

Related: "Other" was split into **Immigration & Asylum** and **Politics & Elections** the same day
(it held 514 of 1,567 candidates). The split runs *only* on the residual path in `classify()`, so
no existing section can lose an item to it — verified by all six original section counts being
byte-identical before and after. `SECTION_NAMES` in shortlist.py and `ORDER` in compose.py must
stay in step: compose.py silently ignores picks under an unknown section name, so a mismatch drops
items with no warning. See [[breakfast-briefing]] and [[briefing-silent-suppression]].
