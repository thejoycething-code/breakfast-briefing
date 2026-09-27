---
name: parl-monitor-backfills-2020
description: Canada and Germany backfills to 2020 started 26 Sept 2026 — costs measured, what was deliberately held back, and the concurrency-group trap when sizing a long run
metadata:
  type: project
---

**Costs, measured 26 Sept 2026** at Sonnet 5 $2/$10 (the 1 Sept rise to
$3/$15 was CANCELLED; src/spend.py fixed in 7305da70 and now prices per day):
- Canada: $0 in API; ~11k requests, ~1.2 GB.
- German triage: $0.0017 per row, 4 rows per call.
- German stance: ~$0.004 per speech, 20 per call.
- Germany to 2020: ~$25-35, mostly ~5,500 speeches from 400 protocols.

**Both repos (parl-monitor and citizengo-meta-reports) report PUBLIC on
GitHub.** This contradicts [[parl-monitor-repo-access]]. It means free
Actions minutes, and a publicly downloadable store. Raised with Christopher;
do not change visibility.

**Canada:** run 36272521032 (backfill=true), dispatched 21:19Z.

**Germany:**
- .github/workflows/de-backfill.yml, first dispatch sized triage 1800s /
  stance 200 so it finishes before the Sunday-pull slots.
- Re-dispatch until the queue is empty.
- NOT backfilled: Vorgänge, committee reports, amendments. de_monitor lists
  every matched row ever, unscored first, so they would flood the edition.
  They need a date window first.
- de_triage now caps at 400 rows, newest first, on a 900s clock. The weekly's
  stance step is capped at --limit 200.

**Concurrency trap:** GitHub keeps ONE pending run per group, and a second
arrival cancels it. A cancelled run fires alert.yml. Size long runs to the
gap, and never dispatch while another run is waiting. Cron drift is real:
the 23:00 EU day sweep started 01:20.

**Coordination:** the "Parliamentary Monitor" session is holding its store
edits (area 13 organ-donation reclassification) until the German backfill's
sidecar commits. Message it when it does.

**Results and follow-ups (26 Sept, 22:00Z):**
- **Canada backfill 36272521032 succeeded**, but covers 45-1 only (May 2025
  on):
  - 137 sittings, 1,059 speeches;
  - 1,188 petitions (408 matched; many are tier 2, needing the judge/gate);
  - 100 Gazette issues;
  - 44-1 divisions.
- **To reach 2020, Canada still needs:**
  - Hansard 43-1 (45 sittings), 43-2 (124), 44-1 (391), via `--session S
    --from 1`. `--backfill` only fills holes below the highest read.
  - Petitions 431/432/441 (304/1,244/2,982). ca_petitions hardcodes prefix
    451, so it needs a prefix option.
  - The Gazette from 2020-01-01.
- **German edition date window: 2878dc60.**
  - Vorgänge (concluded/lapsed) and committee reports 120 days; amendments
    365.
  - Votes by the newest legislature per parliament. A 365-day cut dropped
    Bavaria's scored-3 abortion votes.
  - LIVE Vorgänge are never windowed, and every section discloses what it
    left out.
- **Germany backfill run 36274747181** was dispatched 21:58Z.

**Overnight 26-27 Sept:**
- **Canada combined run 36279171254** reported "failure" only because of 3
  Gazette gaps. Its store (293.5 MB) was published and committed
  (0030ee96).
  - Hansard 43-1/43-2/44-1: 560 sittings, 5,025 speeches, 0 unattributed.
  - Petitions: 432 all and 431 all; 441 cut by its budget at 441-01769.
  - Gazette: 497 issues, 135 matched.
  - The gaps were Gazette typos ("@cs7", "htmlcs10") plus a stated-empty
    issue. Fixed in 5a3a586d.
  - Tail run 36292349282 SUCCEEDED 04:21Z (a56cdaba, 313.5 MB): 441 complete
    (1,213 more, 265 matched) and the 3 gap issues read. CANADA IS COMPLETE
    BACK TO DEC 2019 in every source.
- **German run 2 36288007359** succeeded (42324bc6, 310.1 MB):
  - 212 protocols and 2,229 speeches (5,234 backfilled in total);
  - triage 3,532 scored;
  - stance 401 (200 members).
  - The stance backlog is still ~4,600 speeches: the weekly cap of 200 would
    take months, so dispatch de-backfill with stance_limit=800 in clear
    windows (~$18 left).
- **The "Parliamentary Monitor" session ENDED** before "overnight done" could
  reach it. It must git pull and db_state --pull before its next store push.
- **zsh trap:** `[ a \> b ]` fails in zsh ("condition expected"). Use
  `[[ ]]` or plain bash.

**German stance backlog CLEARED, 27 Sept 09:22Z** (run 36304062119, ee69f236,
314.9 MB):
- 3,406 speeches scored and 485 members placed.
- Unplaced: 1,269 are migration-only (skipped by design) and 8 stragglers,
  which the weekly picks up.
- MEASURED spend since 26 Sept: $25.13 (de-stance $14.44 over 201 calls,
  de-triage $10.03 over 1,340 calls). Lifetime ledger total: $53.38.
- **Both backfills to 2020 are done.**
- Held back: German Vorgänge, committee reports and amendments before 2024.
  The edition now has its date window (2878dc60), so they can be backfilled
  whenever wanted.

**German document layers backfilled, 27 Sept 17:24Z** (run 36335564980,
d6f26152, 320.4 MB, preceded by d9bfcb85):
- Vorgänge: 1,428 seen, 747 new. The term sweep is now paged.
- Committee reports: 9,381, 7,564 new, 231 matched. --pages 60.
- Triage: 863 scored.
- DISKONTINUITÄT rule in de_monitor.by_stage.

**Attribution bug that my 26 Sept backfill caused:** storing legislature
111's votes created a second mandate row per member, so resolve_person's
"exactly one" rule failed. 2,602 of 5,261 speeches were unattributed. The
Parliamentary Monitor session fixed it via de_mdb (0d15a584).

**Canada 2010-2019, probed 27 Sept:**
- Votes, Hansard and LEGISinfo exist for 40-3/41-x/42-1.
- The Senate publishes NO votes before 42-1, and ca_senate calls that a gap.
- The petitions site holds nothing before 42-1. 42-1 is holey (first
  421-00997, sparse to ~4,500), so the walk-with-3-empties reads nothing.
- **Both FIXED on Christopher's instruction (eeac659f):**
  - ca_senate skips sessions before FIRST_PUBLISHED=(42,1).
  - ca_petitions HOLEY={"421":5500}, with a 500-empty tail stop.
  - 42-1 on the site is presented E-petitions only; its paper petitions are
    absent.
  - The ca-weekly petitions cap is 6,000.
  - The Parliamentary Monitor session runs the 2010 Canada backfill Monday
    with older_petitions=true.

**Canadian petitions judge, 27 Sept** (tools/ca_triage.py, 35a12de9; run
36339211908, 1933b1df):
- 1,600 scored: 0: 91, 1: 173, 2: 368, 3: 967. Actual cost $3.81 (400
  calls). It now runs in every ca-weekly, and the weekly's wall is 60 min.
- **The 967 score-3 are only 115 distinct prayers.** MPs present one
  petition dozens of times (top repeats 85, 74, 69, 68). Any edition must
  group identical prayers and count presentations and MPs; the repetition
  count is itself the signal.
- Score-3 by area: MAID 295, free speech 291, religion 264, abortion 220,
  organ donation 116 (forced-harvesting petitions).
