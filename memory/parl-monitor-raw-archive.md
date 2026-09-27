---
name: parl-monitor-raw-archive
description: "data/raw left git on 7 Sept 2026; release `raw-archive`, one tar per day folder, sidecar data/raw.json; pull fetches only changed folders, push union-merges a folder another run published"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T11:31:22.965Z
---

Christopher, 2026-09-07 ("do 3"): the raw archive (287MB, 11,936 files, 31 day
folders, growing weekly) moved out of git the way the store did on 24 Aug.

**Shape.** `tools/raw_state.py --pull/--push`. Release tag `raw-archive`, asset
`raw-<folder>.tar` per `data/raw/<folder>` (uncompressed; contents already gz).
Sidecar `data/raw.json` = {folders: {name: {sha256, files, bytes,
published_utc, published_by}}}, committed. Digest = sha256 over sorted
(relpath, file sha) pairs, so it is content not tar bytes. `data/raw/` and
`data/.raw-pulled` are ignored; history before 7 Sept still carries the files.

**Why the guard differs from the store's.** Raw payloads are write-once by slug,
so two runs archiving into the same day folder are reconciled by UNION: on push,
if origin/main's sidecar holds a digest this copy never saw for a folder, the
tool downloads that tar, extracts beneath local files (never overwriting), and
publishes the union. No `--force`, no refusal. Pull never deletes local files.
Merge driver `tools/merge_raw_sidecar.py` (per-folder, later published_utc
wins) bound via .gitattributes, installed by `--pull`.

**How to apply:** every workflow that pulls the store pulls the archive
(coverage-watch excepted: store-only reader); every one that pushes the store
pushes the archive FIRST; division-watch pushes only (no pull; union handles
today's folder); deploy-tracker pulls and pushes. Never `git add data/raw` (an
ignored path fails the commit step under `set -e`). Monday/Sunday raw steps
carry the `env.SKIP != '1'` guard. See [[parl-monitor-store-artifact]],
[[parl-monitor-store-guard]].
