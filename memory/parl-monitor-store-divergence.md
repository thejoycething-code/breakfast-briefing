---
name: parl-monitor-store-divergence
description: How the parl-monitor store asset and its sidecar diverge, and the three guards that stop it
metadata:
  type: project
---

**The single most damaging failure mode in this repo**, diagnosed and fixed
2026-08-28 after four runs across three workflows died inside half an hour.

The store is a ~95MB release asset; `data/parl-monitor.db.json` is the
committed sidecar naming its sha. `db_state.py --pull` refuses a download
whose sha does not match, and **returns 1, so it fails the FIRST step of any
run**. Nothing heals on its own, because the only step that records a new sha
runs at the END of a successful run.

**Divergence opens whenever a store is published and its sidecar is not
committed.** Three distinct routes, all now closed and all pinned by tests:

1. **The publish ran after the pull was refused.** `Publish the store` was
   guarded `if: always()`, so it uploaded the very bytes the pull had just
   rejected (the pull leaves the download in place, as its message says).
   Each failure republished, so every run saw a DIFFERENT sha. Now guarded
   `always() && steps.fetch.outcome == 'success'`.
2. **The commit was SKIPPED while the publish ran.** `Commit state` had no
   condition, so GitHub skipped it whenever any earlier step failed -- one
   WAF-blocked Senedd feed was enough. **This is where the cascade actually
   began.** Publish and commit conditions are now IDENTICAL in all nine
   publishers, asserted both ways.
3. **The commit FAILED on a push race.** The bot's push lost a race with a
   human push, was rejected "fetch first", and the next run refused the
   store -- the same divergence after the guard was in. All nine now
   `git pull --rebase --autostash` and retry three times with backoff.

**Healing it by hand.** Download the asset to a SCRATCH path (never over the
working store), check `PRAGMA integrity_check` and row counts, then write the
sidecar to match and commit. On 2026-08-28 the asset was AHEAD of my working
copy on four devolved tables -- 6,965 sp_events against 6,580 -- so
publishing my local copy, my first instinct, would have destroyed 385 events.
**Verify which side is ahead before choosing a direction.**

Pushing a store asset from the laptop is blocked by the permission
classifier. That is fine: making CI heal itself is the better fix anyway.

Related: [[parl-monitor-store-artifact]], [[parl-monitor-deferred]],
[[parl-monitor-senedd-waf]].

**A fourth route (31 Aug 2026):** a dispatched or scheduled run pins
`github.sha` at creation; queued behind a publishing run in the shared
concurrency group, it checks out a sidecar OLDER than the asset that run
just published, and the fetch refuses. Needs no failure anywhere. Fixed by
`ref: ${{ github.ref_name }}` on checkout in every parl-monitor-state
workflow, so state runs always act on the branch tip.
