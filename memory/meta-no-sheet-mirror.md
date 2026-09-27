---
name: meta-no-sheet-mirror
description: The nightly Google Sheet mirror was retired 8 Sept 2026; Supabase plus the MCP connector is the delivery path
metadata:
  type: project
---

The Meta reporting pipeline has **no Sheet mirror**. The nightly workflow had a `sync-sheet --push` step gated on `SHEET_ID`; that secret was never set in Actions, so the step skipped silently on every run since it was added and no Sheet was ever created — confirmed by searching Drive for the tab headers it would have written. Retired in `ae8f560`.

**Why:** Supabase is the source of truth and the MCP connector already serves the same data per person, token-gated. A nightly Drive copy adds a second version that drifts (the push clears each tab then rewrites, so a failed run leaves a stale mirror looking authoritative) and puts every post's full text in a shared doc.

**How to apply:** Deliver Meta reporting through the connector tools or a one-off export — `collector/sync-sheet.js` keeps `--out`, `--tsv`, `--csv` and `--push` for manual use. Do not wire any of them back into the nightly. If someone asks for "the Sheet", ask what they want to do with it; the answer is usually a connector query. Related: [[meta-organic-reports]], [[meta-followers-per-post]].
