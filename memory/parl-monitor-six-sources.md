---
name: parl-monitor-six-sources
description: "Six sources added 7 Sept 2026 (amendments, committee reports, UK judgments, regulator consultations, oral statements/UQs, devolved petitions): APIs, gates, what is blocked, where each renders"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T13:02:47.798Z
---

Christopher, 2026-09-07: "Build all of these." All in the Sunday pull (Westminster)
or the sp/sd weeklies (petitions); each sweep in its own try → a gap, never a lost
week. Re-run tool: `tools/pull_sources.py --week YYYY-MM-DD [--only ...]`.

- **Amendments** `src/ingest/amendments.py`: Bills API `/Bills/{id}/Stages/{sid}/Amendments`
  (Take/Skip paging; decisions Agreed / NegativedOnDivision / NoDecision / NotCalled /
  NotMoved / Withdrawn / NotSelected). Table `bill_amendments` holds ALL; items feed
  `amendment` only for on-ground (own text tier 1/watchlist, or watchlist bill flagged
  `all_amendments: true` — 4157 only). News = new or newly decided this week. Section
  "Amendments to watched Bills" after Votes and amendments.
- **Committee publications** `committee_pubs.py`: Committees API, param is
  `PublicationTypeIds` (repeated), types 1 Report / 2 Government Response / 12 Special
  Report. Public site 403s robots → link `committees.parliament.uk/publications/{id}/`
  unverified. Feed `report`, section "Committee reports and Government responses".
- **Judgments** `caselaw.py`: Find Case Law Atom `atom.xml?court=…` (uksc, ewca/civ,
  ewca/crim, ewhc/admin, ewhc/fam, ewhc/kb); text at the `application/akn+xml` link
  (`{url}/data.xml`), fetched archive=False and passage-matched. Feed `judgment`,
  section "Courts".
- **Regulators** `regulators.py`: NICE (HTML table) and NHS England (Citizen Space at
  engage.england.nhs.uk) parse; **Ofcom, GMC, EHRC 403 every non-browser client** →
  declared in `BLOCKED`, recorded as gaps weekly. Land in the deadlines table as
  consultations.
- **Oral statements/UQs** `oral.py`: Hansard `overview/sectionsforday` → `sectiontrees`
  (HRSTag `hs_2cStatement`, `hs_2cUrgentQuestion`) → `debates/debate/{ext}.json`;
  keeps opener + first ministerial contribution. Feed `oral` → Statements section.
  Public URL `hansard.parliament.uk/{House}/{date}/debates/{ext}/` (site 403s curl).
- **Devolved petitions** `dv_petitions.py` + `tools/dv_petitions.py --nation wales|scotland`:
  Senedd = same platform as UK (`petitions.senedd.wales/petitions.json`, thresholds 250 /
  10,000); Holyrood = `data.parliament.scot/api/petitions` (all ever; live statuses
  {3,4,6,10,11}), page `petitions.parliament.scot/petitions/PE####`. Tables
  `dv_petitions`, `dv_petition_snapshots`; companion page groups Westminster / Senedd /
  Holyrood. Never the edition.

**How to apply:** tier-2-only matches need 250 (devolved) / 10,000 (UK) signatures.
See [[parl-monitor-petitions]], [[parl-monitor-build]].
