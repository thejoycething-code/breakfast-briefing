---
name: taxonomy-v16-areas
description: Taxonomy v1.6 added area 12 (prostitution); nothing may hardcode the area count — derive it from taxonomy.yaml
metadata:
  type: project
---

**Twelve areas as of v1.6 (4 Sept 2026).** Area 12 is *Prostitution and sexual
exploitation* — the Nordic-model ground, which no area covered. `prostitution`
MOVED out of area 5, where it had filed the Prostitution (Offences and
Support) (Scotland) Bill and an EP report on regulating prostitution under
"single-sex spaces".

**Adding an area touches five places**, and only the first is obvious:
1. `docs/keyword-taxonomy.md` (the master; regenerate with
   `tools/generate_taxonomy.py` — never hand-edit the yaml)
2. `config/un-taxonomy.yaml` — hand-authored, must carry the SAME areas or
   `test_filter.UnTaxonomyTests` fails
3. `src/digest.py` AREA_NAMES — hardcoded display names
4. `run_monday.py` 5CA loop — was `range(1, 12)` and would have silently
   skipped the new area's sheet
5. tests that hardcoded 11

**Why:** three of those five were literal counts, so the taxonomy grew and the
rest of the system quietly didn't. Two tests now forbid it: no module may
match `range(1, 1X)`, and every area must have a display name.

**Guard conventions worth reusing:** bare `prayer` is substring-matched, so it
hits "World Day of Prayer" and a paint *Sprayer* — guarded terms
(`[with: conversion, ban, ...]`) prove company, not subject, which is why they
belong at tier 2. Bare "sexual exploitation" is excluded from the
parliamentary taxonomy (17 items, mostly child protection, which area 6 owns)
but INCLUDED and guarded in the UN one, where it pairs with trafficking of
adults.

Related: [[parl-monitor-build]].
