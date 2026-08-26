---
name: uk-campaign-calendar
description: Live CitizenGO UK campaign commitments and their delivery dates
metadata:
  node_type: memory
  type: project
  originSessionId: e82fd614-2674-45cc-8361-cb0d786aa13a
  modified: 2026-08-20T13:51:55.135Z
---

CitizenGO UK has a **live assisted dying campaign delivering 4 September 2026**
(confirmed 17 August 2026). It is already running, so the Parliamentary Monitor
does not need to produce a Campaigns Brief for the Terminally Ill Adults (End
of Life) Bill — the brief for that slug was rejected and left rejected
deliberately, not by mistake. See [[parl-monitor-build]].

**The Online Safety Act inquiry: CitizenGO is NOT submitting.** Christopher was
explicit ("We won't be submitting to the OSA. Stop suggesting so."), so never
propose a submission, chase evidence for one, or treat the open call as an
action. An earlier version of this note framed it as open and needing takedown
cases from him; that was wrong.

Its deadline also moved, so do not quote the old one: the Communications and
Digital Committee **extended submission period 3964 from 5pm 7 September to
4pm 21 September 2026**, captured in `data/raw/2026-08-20/` against
`data/raw/2026-08-18/`. Relevant only because a hardcoded 7 September in
tests/test_committees.py broke on it — the call itself is still not ours to
answer.

A rejected brief slug is permanent by design — `make_briefs.py` refuses to
regenerate one even with `--force`. Clearing a `brief_log` row is the only way
back, so check against this calendar before assuming a missing brief is a bug.
