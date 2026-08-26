---
name: parl-monitor-store-artifact
description: The parl-monitor SQLite store is a GitHub Release asset, not a tracked file
metadata:
  type: project
---

`data/parl-monitor.db` is **no longer committed to git**. It reached 92MB
against GitHub's **100MB hard push limit**, growing ~15MB per build sprint
(73 → 88 → 92MB inside four days, Aug 2026), which would have stopped all six
stateful workflows at once. Christopher chose (2026-08-24) to treat it as the
build artifact it is: a **GitHub Release asset** on the rolling `db-state`
prerelease tag, moved by `tools/db_state.py --pull` / `--push`.

**Why not the alternatives (measured, don't re-propose):** per-column gzip
saves only 11.7MB of 34.6MB — short strings never let the compressor warm up;
whole-file gzip saves 81% but git can't delta it; VACUUM saves nothing (empty
freelist); git-lfs free tier can't survive 5 weeklies × 88MB checkouts.
**Vote excerpts are KEPT by explicit instruction** — they carry the Lords
`amendmentMotionNotes` that fixed the inverted amendment scoring.

**Provenance survives as `data/parl-monitor.db.json`** (size, sha256,
producing run), which IS committed and must never be gitignored. `--pull`
verifies the digest and refuses a mismatch.

**Safety rests on the shared `parl-monitor-state` concurrency group** — the
asset has no locking of its own. Actions checkout is depth 1, so there is no
git-history fallback in CI; that's why the migration is two-phase.

**How to apply:**
* **DONE, both phases** (commits d6e9738, 8cf1b0b). Senedd weekly run
  32721990336 (fired manually 2026-08-24) published the first asset; the
  store is now gitignored and untracked. `--pull` fails LOUDLY if the asset
  is ever missing rather than building an empty store. The release is the
  `db-state` prerelease, "Store state".
* **Local work needs a PAT**: add `github_token:` (contents:write) to
  `config/secrets.yaml`, or install `gh`. Without it the laptop cannot fetch
  CI's store and will silently work from a stale copy — the tool says so.
* `data/5ca` was pruned 2026-08-24 (commit e3c299a): 42.7MB -> 12.3MB via
  `tools/prune_5ca.py`, keeping per sheet kind the newest set, the oldest
  (baseline) and the last of each earlier month. Editions themselves are only
  44KB and stay forever.
* **`data/raw` STAYS IN GIT -- decided 2026-08-24, do not re-propose moving
  it.** It is not the store's problem: largest single file is 1.5MB (the
  100MiB limit is irrelevant), and it is APPEND-ONLY, so git stores each file
  once instead of rewriting 88MB per run. Normal growth is <1MB/week (~50MB a
  year); the 210MB is almost all one-off backfill sprints. Moving it would
  actively hurt, because a release asset cannot be appended to -- every run
  would round-trip the whole archive (~17GB/month of transfer) to add a
  megabyte. And the offline re-derivation tools (`retag_passages`,
  `annotate_whips`, `enrich_lords_divisions`, `clean_buffer_zone_noise`,
  `rescore_blind_speeches`) read the historic dirs for FREE re-derivation;
  moving raw would make them "download 210MB first".
* **A sed-derivation guard now exists**: sd-weekly had kept ni-weekly's commit
  message, so the bootstrap run committed as "NI weekly". Tests assert each
  workflow names itself. Deriving workflows by sed is still correct (it fixed
  sp-weekly's day-one double miss) -- just re-read the labels afterwards.

**Backfills must run in CI now** (`.github/workflows/backfill.yml`, manual
only, terms + cutoff inputs). A laptop backfill cannot publish its result
without a PAT, so it strands the work locally while the next weekly
overwrites the shared asset without it. Learned the hard way 2026-08-24.

**The tee trap** (same day): every workflow pipes tools through `tee`, a
pipeline's exit status is the last command's, and GitHub's default `run:`
shell is `bash -e` WITHOUT pipefail -- so a crashed tool reported SUCCESS.
The first backfill run banked a green result with its questions sweep dead.
All piping workflows now set `defaults: run: shell: bash -eo pipefail {0}`
and a test enforces it.


**Scoring also runs in CI** (`.github/workflows/score-stance.yml`, manual,
max_refs + dry_run inputs). It SPENDS MONEY, so the key is written just
before use and removed with `if: always()`, and a dry run publishes nothing.
2026-08-24: 425 refs scored (402 + a 23-ref gap-fill after one batch died on
a truncated JSON response -- the scorer is idempotent, so a re-run fills
gaps and pays nothing twice).

**THE LAPTOP'S STORE IS NOW STALE and cannot be refreshed without the PAT.**
CI is the truth. Do not run anything locally that WRITES to the store until
`github_token` is in config/secrets.yaml -- local writes cannot be published
and the next weekly overwrites the asset without them.

See [[parl-monitor-build]].
