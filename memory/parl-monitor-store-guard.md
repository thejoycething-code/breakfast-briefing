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
