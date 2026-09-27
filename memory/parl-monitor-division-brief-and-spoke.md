---
name: parl-monitor-division-brief-and-spoke
description: "Division brief (same-day DM + data/briefs file, no verdict) and Who spoke and which way (per-debate stance tables) built 7 Sept 2026; Hansard sweep window bug; both-lobbies abstention trap"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T07:33:25.971Z
---

Built 2026-09-07 on Christopher's instruction, ahead of the TIA Second
Reading on Friday 11 September 2026.

**Division brief.** `tools/division_brief.py` + `division-watch.yml` (Mon–Thu
18:00/21:00 UTC, Fri 13:00/15:00/17:00 UTC, dispatch with date/force). For each
division on our ground it writes `data/briefs/division-<c|l><id>.md` (result,
party splits, anchor lobbies, lobby changes vs the comparable vote, full name
lists by lobby) and sends ONE DM per run. Idempotent on the file, touches no
store. It attaches no meaning: `prep_division.py --our-side` still signs the
verdict, and vote_tracker.yaml stays editorial.

**Who spoke, and which way.** `src/spoke.py` collects debates from mp_events
kind='debate' joined to `stance` (why + -2..+2); `digest.render_spoke` renders
one table per debate, leading the Parliamentarians section; debates then leave
the one-line list. Direction words: With us (strongly) / Neutral or unclear /
Against us (strongly) / Not yet scored. Caps 15 speakers, 8 debates.

**Why:** two traps found on the way. (1) The weekly Hansard sweep searched the
EDITION week (not yet happened), so no speech since 23 July was ledgered until
the backfill of 24 Jul–6 Sep (45 events). Divisions had the same bug fixed
earlier; any new sweep must use report_start/report_end. (2) A member recorded
in BOTH lobbies is the Commons' deliberate abstention (Wendy Chamberlain, 2025
Third Reading); comparing name lists naively reports a phantom lobby change.

**Deploy tracker** (`deploy-tracker.yml`, manual): pulls the store read-only, runs the
suite as a gate, rebuilds the tracker, deploys Vercel, commits the pages. Friday
sequence: brief DM → read question → prep_division --our-side → edit
vote_tracker.yaml → push → `gh workflow run deploy-tracker.yml`. Vercel prints
Inspect/Production to STDERR: capture 2>&1 or a summary grep fails the step.
No mid-week alert for now (Christopher, 2026-09-07).

**How to apply:** rehearsal = `division_brief.py --date 2025-06-20 --force --no-dm --out <tmp>`.
Score stance dispatched once (50 refs) to seed directions for Edition 6; the
Sunday pull scores the rest weekly (cap 400). Closed consultations now drop off
the deadlines table; Across the parliaments is unwired (src/across.py kept for
the EU gap tests). See [[parl-monitor-week-ahead-table]], [[parl-monitor-build]].
