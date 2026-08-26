---
name: lead-ad-builder
description: Standalone web tool that generates a Google Doc brief for Meta Lead Form Ads
metadata: 
  node_type: memory
  type: project
  originSessionId: 712bb778-3691-4eeb-a200-2028eefe4569
  modified: 2026-08-16T21:31:59.114Z
---

Lead Ad Form Brief Builder — a self-contained static web tool at `~/Downloads/lead-ad-builder/index.html` (+ `logo.png`, `README.md`). Outreach fills in approved Lead Form Ad components; it generates a Google Doc brief the campaigner uses in Meta Ads Manager.

Built 2026-07-24 from the internal guide Google Doc `1bPgZ034s0eI8rOG4MfBV3Gw8VsZV8LwMGC7fYjpBoe4` ("How to Create and Launch Facebook Lead Form Ads"). Output = download `.doc` (opens in Google Docs/Word) + copy-to-clipboard rich HTML. No backend/build step; deploy as static to Vercel like [[clacton-vercel-deployment]].

**Rendering gotcha (2026-08-16):** the campaign blocks must stay as STATIC HTML in the page (one full campaign block lives inside `#campaigns`), with JS capturing it as `CAMPAIGN_TPL`/`OPTION_TPL` via `cloneNode` and `addCampaign`/`addOption` cloning it. Reason: the Claude Code preview pane renders files outside the primary project folder as no-JS static snapshots, so a purely JS-rendered form showed as blank ("can't see the editable blocks"). Do NOT go back to building the first campaign from a JS string template — keep the static-first-block + clone pattern so it renders without JS.

**v2 model (after seeing the real campaigner brief `14ORNj_zZ3Tc5-BztJV5jPve98VsO0hUqO8bD4TTeMwQ`, which bundles UK+AU+CA as three fully-independent campaigns):** one brief = multiple **self-contained campaign blocks** (Add another campaign; each collapsible, removable). Each campaign owns ONE list (single-select flag combobox, searchable by code/country/language), optional per-campaign Petition ID, its own strategy/audience/creative-options(A/B/C)/form/consent/budget/duration/lead-campaigner. Internal name per campaign `YYYY-MM | List | Leads | Petition ID | Title`. The earlier shared-multi-list model was dropped as it didn't match reality. `LISTS` array (25 lists, `{code,flag,country,lang}`) at top of the script is the single edit point. Creative images link to Google Drive via pasted share links (smart-detect, no OAuth).
