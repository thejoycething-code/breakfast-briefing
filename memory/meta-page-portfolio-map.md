---
name: meta-page-portfolio-map
description: "Which Business Portfolio owns which CitizenGO Facebook Page — derived 25 Aug 2026; two portfolios hold 16 of 22 pages, 13 pages belong to none"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 627528f6-d990-498b-a0b6-67f293a96686
  modified: 2026-08-25T02:09:36.160Z
---

Page-to-portfolio ownership for [[meta-organic-reports]], derived via
`ads_get_pages_for_business` across every business ID (12 calls).

| Portfolio | Business ID | Pages |
| --- | --- | --- |
| **citizenGO** | `731536880628289` | **11** — CitizenGO (117,665 followers), HazteOir.org, France, Deutsch, Brasil, Latam, Africa, Australia, Slovensko, Hrvatska, Magyarország |
| **Citizengo** | `601231733400213` | **5** — Derecho a Vivir, Aborto Cero, Más Libres, Nederlands, Stop genderwaanzin nu |
| CitizenGO Italia | `646698305684148` | 1 — Italia (`928073553889078`) |
| Citizengo USA | `1513338093267905` | 1 — USA |
| CitizenGO Canada | `377140928214536` | 1 — Canada |
| CitizenGO Argentina | `415071818980744` | 1 — Argentina |
| Citizen GO Québec | `1353718589963989` | 1 — Québec |
| Joyce.Digital | `923306969035797` | 1 — **Citizen GO UK** (the only page collecting) |

Own **no** pages: HazteOir.org (`985627071455635` and `452858999152739`),
Citizengo Scotland (`1074077644943243`), Citizengo Australia (`2031437807454163`).

**Why this matters:** the rollout looked like "34 pages across 12 portfolios" but
the work is concentrated — one System User in `citizenGO` unlocks 11 pages at
once, and two portfolios cover 16 of the 22 owned pages.

**CORRECTED 26 Aug 2026.** The first version derived businesses from ad accounts and
found only 12. `ads_catalog_get_businesses` returns **18**. Five pages previously
recorded as belonging to no portfolio in fact do:

| Page | Portfolio | Business ID |
| --- | --- | --- |
| Citizen GO Ireland | Citizen GO Ireland | `302772972450120` |
| Citizengo México | Citizengo Mexico | `1658962955406804` |
| España unida siempre | Hay España Unida | `239254857752290` |
| Orgulloso de ser Cristiano | Hazte orgulloso cristiano | `218317092309988` |
| Derecho a la vida | Haz Derecho a la vida | `407058837243133` |

Own no pages: Citizengo Deutsch `1037948362543889`, HazteOir Ads `1280562753954919`.

So **27 of 35 pages sit in a portfolio**, not 22, and only **8** are personally
admin'd: Yo educo a mis hijos, Sanchez No, Vivir en Familia, CitizenGO Österreich,
VotaValores, Citizen GO Schweiz, Citizen GO België, Citizen GO Scotland.

**How to apply:** enumerate businesses with `ads_catalog_get_businesses`, never by
inferring them from ad accounts — that misses portfolios with no active ad account.
Also note `923306969035797` now reports as **Citizengo UK**, though the ad-accounts
endpoint called it Joyce.Digital; confirm which before treating it as personal.
**Redes HO is an ad account with no owning business, not a portfolio** — a System
User cannot live there.