---
name: ig-video-transcription-feasibility
description: Probed 21 Sept 2026 — IG Graph gives a fetchable mp4 via media_url but no transcript field, so transcribing Reels means download plus ASR
metadata:
  type: project
---

Transcribing Instagram Reels is **possible but entirely on us**. Probed live on Graph v23.0, 21 Sept 2026, by `scripts/probe-ig-video-source.js` (Actions → "Probe metric coverage"), on three real Reels:

- `media_url` **is returned** for VIDEO media, and the URL genuinely serves the file: `HTTP 206`, `content-type: video/mp4`, content-range reporting 16,115,763 / 5,396,642 / 3,067,726 bytes. Roughly 3–16 MB per Reel.
- `captions`, `transcript` and `source` are all **refused with HTTP 400** — the fields do not exist on IG media. `video_title` and `alt_text` are accepted but come back undefined.

So Meta hands over the video and nothing about its content. Any spoken-word or on-screen text has to be produced by us: download the mp4, then ASR (or frame-sample plus OCR for burned-in text).

**Why:** the whole question was whether this was a data-collection job or a media-processing job. It is the second, and that changes the shape entirely — a service dependency, per-minute cost, and a pipeline that handles binaries rather than JSON.

**How to apply:** scale is small — 402 VIDEO posts total, 85 in the last 30 days, oldest 2026-05-31 — so the back catalogue is about 3 GB of downloads, not a budget item. Treat `media_url` as **short-lived**: it is a signed CDN URL, so fetch it in the same pass that requested it rather than storing it and fetching later; re-requesting it is one cheap Graph call. Re-run the probe whenever `GRAPH_VERSION` moves, since the answer is version-specific. The post caption is a different thing and is already collected — see [[meta-organic-reports]]. Related: [[meta-graph-error-1-deterministic]], [[meta-followers-per-post]].

**Built 21 Sept 2026.** `collector/transcribe-ig.js` + `.github/workflows/transcribe-ig.yml`, whisper.cpp `small` on the runner — nothing goes to a transcription API. Table `meta_ig_media_transcript`, view `meta_ig_searchable` (LEFT join onto `meta_ig_latest`), and `search_posts` now matches caption OR spoken word and labels which.

Three things the first real runs taught, each of which had to be fixed:
- **ffmpeg is not preinstalled on ubuntu-24.04.** Three Reels failed `spawnSync ENOENT` before the apt step existed.
- **A silent video is settled, not failed.** ffmpeg says "Output file does not contain any stream". Recorded as an ordinary error it would be re-downloaded on every run forever and coverage would never read complete, so those get a `no-audio: ` prefix and are excluded from the pending list.
- **Throughput is roughly 1× real-time** on the 2-core runner with `small` (59.4 s of audio took ~52 s; 28.2 s took ~30 s). 402 Reels ≈ 5 h of audio ≈ 5 h of runner time, and **the repo is private so those minutes are billable**. Run it in batches with `--limit` / `--budget-minutes`; the workflow's concurrency group means only one queued run survives, so dispatch batches one at a time rather than four at once.

**How to apply:** `scripts/transcript-coverage.js` prints coverage, languages and failures-by-reason and runs `if: always()` at the end of every transcription job — read it rather than the job's green tick. Registering a new table in `scripts/check-supabase.js` is not optional: `db:schema-check` fails with "in the DDL but not checked by the preflight" until you do.

**Some Reels never yield a file, and Graph will not say why.** About 6% (8 of the first ~143) answer `HTTP 200` with `media_url` simply omitted. Probed twice, hours apart, against controls from the same page and the same day (`scripts/probe-missing-media-url.js`). Ruled out: **token, page and permission** (controls on the same page returned the URL); **ownership** (`owner.id` is identical on subjects and controls, and is the page's own `ig_user_id`, so these are not collab or shared posts); **a copyright flag** (`copyright_check_information` reads `not_started` on both sides); **the post being unhealthy** (reach 15k, views 21k, interactions on par with the rest, nothing null); **transience** (still absent on every retry). `music_metadata` and `alt_media_url` do not exist in v23.0.

**The cause is undetermined.** Licensed audio remains the untested hypothesis — Graph exposes no field for it, so it cannot be checked from the API. What *is* settled is that the absence does not change between calls.

**How to apply:** those rows carry a `no-media-url: ` prefix and are excluded from the pending list, so they do not burn a Graph call every run — but under their own prefix, separate from `no-audio: ` and `no-speech: `, because those two are understood and this one is not. `--redo` re-attempts them if it ever starts working. The coverage report states the percentage of the files we can **actually fetch** alongside the raw percentage, so a permanently unreachable tail does not read as a pipeline that never finishes. A Graph *error* is still a real failure and still retries; only a clean 200 with no field is settled.

