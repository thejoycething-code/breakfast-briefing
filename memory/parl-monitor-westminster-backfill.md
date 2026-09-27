---
name: parl-monitor-westminster-backfill
description: "Westminster ledger depth (8 Sept 2026): complete to Jan 2020; 2017 Parliament added (speeches, PQs, EDMs); 2020-21 thinness is real not a term gap; divisions of that era need the candidate finder, not the title sweep; backfills must run one at a time"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-08T16:02:17.039Z
---

Christopher, 2026-09-08: "use some of our remaining allowance to increase the
backfill of data we need, maybe in Westminster".

**State after the run.** mp_events reaches back to June 2017 for speeches, PQs and
EDMs (2017 Parliament added: 1,831 speeches, 906 PQs, 277 EDM events, 1,121 of the
speeches by 307 members still sitting); votes to 2020 plus the 2017-19 divisions a
title search can see (one). 2020-21 re-swept with today's 45 terms: only 45 new
speeches and 12 new divisions, so the thinness of those years is the pandemic
Parliament, not missing terms. Stance: 2,687 refs scored on 8 Sept for $10.45 (135
calls; about 0.4 cents a ref); 266 refs stay unscored because no evidence text is
recoverable from data/raw. Weekly cap is 400 refs; anything bigger is a flagged spend.

**Traps.** (1) The votes APIs search TITLES, and the 2017-19 votes on our ground were
amendments with procedural titles (9 July 2019 NI Executive Formation Bill: NC1 McGinn
abortion, NC10 Creasy same-sex marriage). `tools/find_division_candidates.py` finds
them through same-debate speeches; its queue is data/division-candidates.json (43 for
2017-19) and a HUMAN adds the ones that belong to config/vote_tracker.yaml with a
meaning line. Never ledger them by script. (2) backfill_hansard.py and
backfill_mp_ledger.py said they were safe to run concurrently; they were not under load
("database is locked" killed the Hansard run after 74 events) until the same day's fix,
intel.write_with_retry, which rolls back, waits and retries. Concurrent backfills are
fine since then; watch the logs for retry lines. (3) hansard_sections holds only Sept 2026 locally; a six-month sections backfill
is free but feeds only diary links, so it was left.

See [[parl-monitor-build]], [[parl-monitor-store-artifact]], [[parl-monitor-5ca-surfaces]].

**Later on 8 Sept (Christopher: "Do 2, then 1, then 3, then 4").** (2) Ledger writes now
retry through "database is locked" (intel.write_with_retry), proven by three backfills
running together. (1) Review queue docs/division-candidates-review.md: 130 displayable
divisions 2020-26 and 7 for 2017-19, none ledgered by script. (3) 2015 Parliament added:
2,133 speeches, 538 PQs, 511 EDM events; divisions API has nothing before 2016. (4) THE
BIG FINDING: the Hansard sweep reused pq_sweep_terms, which omits the plain words
("abortion", "assisted dying", "free speech", "marriage"...), so it never searched for
them; 37 of 38 abortion speeches on 9 July 2019 were missed. Fixed with
settings.hansard_extra_terms + hansard.sweep_terms (weekly and backfill), page cap 6,000
and logged. The Hansard search API answers HTTP 500 for some term-and-window pairs
("home education" 2019 fails for the year and for July, answers for Jan-Mar):
search_contributions_split bisects to a week. A store-dependent test
(test_every_sitting_title_in_the_store_is_matched) broke on the new "Sitting Hours"
debates and was narrowed to real suffixes.

**Credit ran out mid-run, 8 Sept 2026 evening; topped up 9 Sept.** The displayable
scoring run (7,312 refs, --skip-hidden) scored 439 then every batch failed with "Your
credit balance is too low to access the Anthropic API"; that day's stance spend was
$12.40 (157 calls). Christopher added credit on 9 Sept and the backlog was resumed.
The lesson to keep: EVERY API pass shares the one key in config/secrets.yaml (the
weekly judge and stance, devolved and EU triage, a debate pack's stance read), so an
exhausted balance degrades the whole monitor at once -- the tools record gaps rather
than crash, which means a green run can hide a missing judgement. `score_stance.py`
is idempotent and stores per batch, so an interrupted run costs nothing already paid
for; re-run `--skip-hidden` to fill displayable ground first.

**Tracker divisions were hollow IN THE LEDGER (found 10 Sept 2026, fixed).** Precision
matters here because I overstated it once. The tracker PAGE renders voters from the raw
archive payloads and was never wrong for the older divisions (diff of the regenerated
page: unchanged). The LEDGER -- which the 5CA placements and the stance scorer read --
had no voters for any tracker division whose title named no issue (report-stage new
clauses, Lords amendments), because only the title-based sweeps fill it. So those votes
contributed nothing to any member's placement. First run of the new guard found 13 of
23 signed-off divisions in that state: NC142/NC143 (added that day), but also the
buffer-zones votes 1368/1491, abortion decriminalisation 2058/2059, non-crime hate 2060,
parental rights 1580/1727/1957 and three Lords assisted-suicide divisions 981/1885/1886.
Fix: `src/trackerledger.py` + `tools/ledger_tracker_divisions.py`, run in run_monday
BEFORE make_vote_tracker; idempotent; Lords via `house: lords` -> prefix `div:l`.
The review doc's old claim that "the Score stance run ledgers the voters" was false.
Rule: config/vote_tracker.yaml is the list of divisions we care about; the ledger follows
it, never the other way round.
Verified on the regenerated 5CA (10 Sept): Hinder, Stringer, Glindon and Caroline Johnson
are all placed ++ on area 3 with `div:c2421:aye` as the DECIDING evidence, so the sign-off
now does what it claims. Gotcha: `stance.suggest_rows(as_at=...)` filters by the EVENT
date, not when a row was ledgered (mp_events has no ledgered-at column), so it cannot show
"what did today's ledgering change" -- a vote dated 8 Sept appears in a 10 Sept as_at too.
And the sheet renders placement + comment, never the division ref, so grepping a sheet for
"New Clause 142" proves nothing either way.

