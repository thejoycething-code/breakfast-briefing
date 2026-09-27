---
name: parl-monitor-store-guard
description: db_state --push refuses a store whose lineage this copy never held; coverage.py watches pipelines, feeds, and green-run-over-stale-data
metadata:
  type: project
---

**The incident (3 Sept 2026).** The UPR monthly harvested 1,218 new UPR
recommendations, published the store and committed its sidecar at 06:20. At
09:58 a hand push from this laptop published a store that predated that run,
overwriting the release asset and the pointer. Every workflow stayed green.
The loss was found a day later only by measuring how stale each source was.

**Three defences now exist:**

1. `tools/db_state.py --push` refuses to publish unless the sha on
   origin/main's sidecar is one this working copy has held (`data/.store-pulled`
   keeps the full list — pulled AND published, because a push writes locally
   before the sidecar commit reaches origin). `--force` overrides and says
   what it discards. It fails OPEN when git can't answer.
2. `source_runs` — a heartbeat per WORKFLOW, stamped inside the bytes by
   `--push` before the sha is taken. Westminster's tables carry no
   `captured_at`, so nothing else could tell whether the Sunday pull ran.
3. `tools/coverage.py` + `.github/workflows/coverage-watch.yml` (daily,
   read-only, watched by the failure alert).

**Why:** each signal alone looked healthy — UPR's pipeline had run 24 hours
earlier and its data was 19 days old. The check that catches it is the
CROSS one: a pipeline whose heartbeat is fresh but whose feeds are older
than its own run either stored nothing or was overwritten.

**How to apply:** freshness is judged by when we last SAW a source
(`last_seen`/`captured_at`), never by the date of the business — recess is
not an outage. Feeds written once per item (`ni_sittings`, `ni_sponsors`,
`eu_speeches`) are listed, never failed. A paused pipeline is named with its
reason, because a pause nobody records reads as health.

**Sequencing rule, paid for 6 Sept:** a dry-run Monday publish PUBLISHES the
store and commits the sidecar (only Slack/Asana are held back). So: (1) never
dispatch a dry run while a local store push is pending — it moves the pointer
and the guard will (correctly) refuse you; (2) never dispatch anything until
`git push` has actually succeeded — a stuck rebase on the sidecar left origin
pointing at an old sha while the asset was new, the next run refused the store
with SHA MISMATCH, and the failure alert fired. Order is always: pull → work →
push store → commit → push git (verify) → dispatch → live. Gate each step on
the previous one's exit status; `for attempt … done` without a success check
is how the cascade started.

**The pointer file merges itself (7 Sept 2026):** `tools/merge_sidecar.py` is a git merge driver for `data/parl-monitor.db.json`. Rule: the side that names the asset the release ACTUALLY holds wins (GitHub exposes the asset digest via the API, no download); fallback: later `published_utc` (safe because the lineage guard forbids publishing an older store); neither: exit 1, human resolves. "Take mine" was right three times and is wrong in general. `--pull` installs the driver in local config on every clone/runner because `.gitattributes` alone is not enough.

Related: [[parl-monitor-store-artifact]], [[parl-monitor-store-divergence]].

## Never pipe db_state into tail (repeated 11 Sept 2026)

`python3 tools/db_state.py --pull | tail -1 && ...` ran the whole chain on a REFUSED pull
because the shell saw tail's exit code. The ledger then wrote into a stale local store
and the push was (rightly) refused. Same trap as finish.sh on 9 Sept. **How to apply:**
redirect to a log file and test `$?`, or `set -o pipefail`; and always `git pull` before
`db_state --pull` — the pull verifies against the COMMITTED sidecar, so a stale checkout
makes a good asset look divergent.

**Cancelled is the silent one (19 Sept 2026).** GitHub reports a job that hits
`timeout-minutes` as *cancelled*, not failed, and alert.yml fired on `failure`
alone, so the EU weekly died twice at the written-question drain (14 min of
pulls and body reads, then 300 detail fetches sitting in 429 backoff) and the
triage, edition, tracker and 5CA steps were skipped with no DM. Now: the alert
fires on failure/cancelled/timed_out and names it; the weekly has 60 minutes
and `PYTHONUNBUFFERED=1` (buffered stdout into `| tee` left a killed step's log
empty); the EP drains carry a wall clock (`src/drain.py`, 600s) because a
count cap bounds the API, only a clock bounds the job. Never pipe a suite
through `tail -3`: unittest's verdict is on stderr, test prints buffer on
stdout, and the verdict is what `tail` loses.

**Monday publish (21 Sept 2026).** `gh workflow run monday-publish.yml` with no
input is a DRY RUN (`dry_run` defaults to true): it judges, renders and deploys
but posts nothing, and the crons still owe the week. The publish is idempotent
per week via `publish_log`, so a hand dispatch never doubles a late cron. The
crons drift 3-5 hours on this repo; a 30-minute wall killed the run inside
`run_monday.py` after the devolved judge (8 min, ~76 calls) and the renders,
somewhere in the tool list (roster, trackers, 5CA, briefs, Drive). Wall is 60
now and the step is unbuffered.
