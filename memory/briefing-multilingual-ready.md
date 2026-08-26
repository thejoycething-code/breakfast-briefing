---
name: briefing-multilingual-ready
description: "The Breakfast Briefing classifier handles Spanish and Italian, but the non-English sources are deliberately parked as comments in extra_feeds.txt"
metadata: 
  node_type: memory
  type: project
  originSessionId: 84d457ef-6b54-4c7b-8bd0-1fe284f8e407
  modified: 2026-08-13T16:06:12.567Z
---

The Breakfast Briefing classifier speaks Spanish and Italian as of 13.08.2026, but the
briefing stays English for now (Chris: "Keep it mostly English for now but have the sources
ready for the future").

**What is live:** `shortlist.ML_SECTIONS` carries Spanish and Italian vocabulary for all six
specific sections, merged into `COMPILED` rather than edited into the English `SECTIONS`
tables so it cannot disturb existing behaviour. `OTHER_ALLOW`, `CHAFF_RESCUE`, `OUTCOME`,
`PROCESS` and `SCALE` are extended by appending to `.pattern`. `fetch_feeds.KEYWORDS` has the
matching prefilter terms. These are inert while no non-English sources are active.

**What is parked:** six verified feeds sit commented out at the end of `extra_feeds.txt` —
Religión en Libertad, InfoCatólica, Infovaticana, ACI Stampa, Tempi, Le Salon Beige. Each was
fetched and parsed, with item counts recorded. Uncomment to enable. ACI Prensa
(aciprensa.com) is the significant one still missing and needs a manual look.

**Two language traps worth remembering**, both caught by testing and both silent failures:
Spanish news headlines use the **present tense** ("el Supremo *anula* la ley"), so a
preterite-only outcome list scores real rulings as commentary; and Spanish and Italian invert
participle word order ("Detenido un sacerdote", not "sacerdote detenido"), so patterns
written in English order miss them. Test any new language on real headlines, not invented
ones — 14/15 on real headlines after fixing these, 12/15 before.

Related: [[breakfast-briefing]], [[briefing-ranking-single-pass]], [[briefing-silent-suppression]]
