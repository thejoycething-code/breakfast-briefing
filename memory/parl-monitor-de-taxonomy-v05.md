---
name: parl-monitor-de-taxonomy-v05
description: German taxonomy v0.5 — scan the Bundestag's own descriptors to escape circular recall tests; inner * was a literal (four dead terms); retag additively only
metadata:
  type: project
---

26 September 2026, Christopher: "Scan the Bundestag yourself and determine
any additions." Result: v0.5, 21 terms added, four dead terms revived.

**How to apply:**

- **Escape circular recall tests with DIP descriptors.** A probe list you
  write can't find words you don't know. `tools/de_taxonomy_scan.py` seeds
  from tier-1 terms (ALL time, `f.titel`), harvests `deskriptor`
  (`typ == "Sachbegriffe"`) from those Vorgänge, then expands each uncovered
  descriptor via `f.deskriptor` — Vorgänge chosen by the Bundestag's
  indexers, not us. Split the expansion budget PER AREA: ranked by seed count,
  migration took 18 of 60 and the thin areas got none.
- **"Missed" is not quality.** Broad descriptors (Krankenkasse) miss 99%
  correctly. Measure each candidate against DIP and READ samples.
- **A `*` inside a phrase used to be a literal asterisk** in
  `src/filter.py:_compile_term`. `"ungeborene* Leben"`, `"assistierte*
  Selbsttötung"`, `"Trans* bei Kindern"` (all DE tier 1) and EN
  `"smartphone* in schools"` never matched. Fixed (`\w*`); `EveryTermCanMatchTests`
  fails if any term can't match its own spelled-out form.
- **Reviving a dead term can make it over-broad.** `Trans\w* bei Kindern`
  hit Transferleistungen/Transport/Transparenz. Test newly-live terms
  against plausible false positives, not just intended matches.
- **Retag additively only** — `tools/de_retag.py`. A single-field re-derive
  would have cleared 52 correct tags (speeches classified on full body,
  divisions on label+topics+inheritance). Compare v_old vs v_new on the SAME
  field before trusting any "lost" count.
- **Biggest real gap was religion:** "Lage der christlichen Minderheit im
  Jemen" — `christliche*/religiöse* Minderheit*` (22/24 Vorgänge, ~all missed).
- **Reserved to the German team, measured:** `Euthanasie*` is 19/23 Nazi-era
  commemoration (83% FP, tier 1); intersex.
- **Organ donation IS in scope for Germany** (Christopher, 26 Sept), area 2;
  Organhandel in 12. 156/156 DIP Vorgänge match.
- **An area needs BOTH layers.** Taxonomy = candidates, judge = what reaches
  the edition. Organ-donation speeches were tagged, then scored 0–1 "outside
  CitizenGO's campaign scope" until `SYSTEM_PROMPT_DE` named the area. When
  adding an area, update the judge prompt and RE-SCORE rows scored under the
  old one (null `triage_score`, re-run `de_triage`). Test:
  `TaxonomyAndJudgeAgreeTests`.
- **`de_speeches --reread` forgets EVERY protocol.** To re-read one sitting,
  delete just its `de_protocols` row.
- **Another session may share the checkout** (Canada work, 26 Sept). Commit by
  explicit path, never `git add -A`; verify your store edits survived before
  pushing — the store file is shared.

Related: [[parl-monitor-germany]], [[parl-monitor-de-keyless]],
[[parl-monitor-pq-full-text]].
