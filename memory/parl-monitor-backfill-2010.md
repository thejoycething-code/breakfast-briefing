---
name: parl-monitor-backfill-2010
description: "Backfill to 2010 approved 27 Sept 2026 (~$65); run plan and windows, what the sources hold, and the German attribution fix it needed first"
metadata:
  node_type: memory
  type: project
  originSessionId: ca83064b-4f54-4a71-9507-09fdb62967c3
  modified: 2026-09-27T17:21:21.293Z
---

Christopher approved "Run it back to 2010" on 27 Sept 2026, estimated at ~$65 (Germany ~$37, Westminster ~$28, Canada $0). It is well beyond the usual weekly spend. If a run heads far over budget, stop and ask.

**What the sources hold (probed 27 Sept):**
- UK written questions only from 2014; the Commons divisions API only from 2016. EDMs and Hansard reach 2010. The ledger started at 2015-05-19 (debates), 2015-06-01 (PQs) and 2014-06 (EDMs).
- The German DIP protocols parse for WP17/18 (17/187: 253 speeches, 35 on our ground).
- abgeordnetenwatch Bundestag legislature ids: 83=2009-13 (94 votes), 97=2013-17 (121), 111=2017-21, 132=2021-25 (162, NEVER collected before, including the July 2023 Sterbehilfe votes), 161=2025-29.
- Canadian Hansard and votes parse for 40-3 and 41-1. E-petitions exist only from 42-1 (Dec 2015).

**German attribution fix (0d15a584), done first:** 2,609 of 5,386 speeches were unattributed. de_members holds one row per MANDATE, and once 111 was stored beside 161, members of both terms matched twice. resolve_person now maps each mandate to a person via de_mdb + de_mdb_terms and takes the latest mandate. On the live store: 1,976 recovered, 0 lost, 0 moved. The remaining ~633 are mostly 132-term members, fixed by collecting 132. The --reresolve store write happens inside the de-backfill run (new step). The register lags the current term (Breilmann), so the term check applies only to shared names.

**Run plan.** GitHub keeps ONE pending run per state group: a run may span one scheduled slot, never two.
1. Sun 27 Sept, after the 21:00 de-weekly: de-backfill with since 2010-01-01, until 2019-12-31, legislatures "83 97 132", sized to end before Mon 02:00.
2. Mon 28 Sept, ~07:45-18:00Z (clear window):
   - backfill.yml Westminster in two windows: 2012-10-01 to 2015-05-18, then 2010-01-01 to 2012-09-30.
   - score-stance.
   - ca-weekly with older_sessions "40-3 41-1 41-2 42-1", older_petitions=true, gazette_since 2010-01-01 (may need two runs). Option B (Christopher, 27 Sept) is pushed by the Canada session: ca_senate skips pre-42-1 sessions without a gap, and ca_petitions scans 42-1's holes automatically (no new input, ~40 min, 6,000-fetch cap).
The Canada session ("Canadian parliamentary monitor groundwork") shares the group. Tell it before each dispatch.

See [[parl-monitor-backfills-2020]], [[parl-monitor-westminster-backfill]], [[parl-monitor-store-guard]].
