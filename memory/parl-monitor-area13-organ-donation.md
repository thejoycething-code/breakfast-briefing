---
name: parl-monitor-area13-organ-donation
description: "Organ donation is area 13 (EN v1.9, DE, UN) since 26 Sept 2026; held from stance/5CA until position stated; store repair pending after German backfill"
metadata:
  node_type: memory
  type: project
  originSessionId: ca83064b-4f54-4a71-9507-09fdb62967c3
  modified: 2026-09-26T21:52:57.011Z
---

Area 13 "Organ donation and transplant ethics" was added 26 Sept 2026 (commit 5846dd7d). Before that, German organ terms sat in area 2, which would have put organ speeches on the assisted-dying stance, issue pages and 5CA.

- POSITION (confirmed 26 Sept, commit 9936a8a2): supports freely given donation; opposes presumed/deemed-consent opt-out, forced harvesting, organ trafficking and transplant tourism. It's in the stance, triage and debatereport prompts. Promoting donation scores 0. NO_POSITION_AREAS is now () (mechanism kept for future areas). No 5CA sheet: 13 is in excluded_from_5ca in config/stance_overrides.yaml, per "wire it in with no 5CA sheet".
- UK sweeps don't derive from the taxonomy. pq_sweep_terms has organ-donation/organ-transplant/organ-harvesting; edm_sweep_terms has organ donation/organ harvesting. deemed-consent was rejected (its newest PQ results are "Flags").
- Bare `transplant*` was rejected from EN tier 2: it tagged kidney days, stem-cell funding and a charity run. German `Transplantation*` is fine because the matcher anchors at word start.
- Stance evidence for areas 2 and 13: organ trafficking and forced harvesting belong in 13, not 8 or 12.

**Store repair DONE 27 Sept (sidecar 40924484, store sha b109e0cb9c83):** 15 German rows moved from area 2 to 13, 65 ledger rows and 8 Holyrood motions gained 13, and the Westminster drift was applied (239 rows gained an area, 0 cleared).

EU tables RESOLVED 27 Sept (3c61f36f): the mapping was wrong, not the tags. retag_items now has DERIVERS: eu_texts uses the title plus the archived body passages (data/raw/*/eu-texts_doc-<id>.json.gz holds gzipped .docx despite the name), and eu_divisions uses the SUBJECT label (before " — "), else the inherited text's areas. Both reproduce 100% under v1.8 and change by 0 rows under v1.9, so there was no store write.

The German backfill run 36274747181 ran on the OLD code (13 held), so its organ speeches get stance on the next de_stance pass.
