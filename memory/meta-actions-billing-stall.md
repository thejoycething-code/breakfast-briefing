---
name: meta-actions-billing-stall
description: 22-23 Sept 2026 collection stopped because GitHub Actions billing refused jobs, not a token or code fault; Reels transcription burned the minutes
metadata:
  type: project
---
On 22 and 23 Sept 2026 the Meta "Nightly collection" workflow failed in ~4s both nights. Cause: GitHub refused to start the job ("recent account payments have failed or your spending limit needs to be increased"). The likely trigger was repeated "Transcribe Instagram Reels" workflow_dispatch runs on 21 Sept (one lasted 3h12m) using up the private repo's Actions minutes. Watchdog was refused too. Once billing was fixed, a manual dispatch succeeded and freshness went back to 0 days.

**Why:** the watchdog DM's cause list (token expiry / failed run / cron disabled) doesn't cover billing. A 4–5s failure means GitHub never started the job, so the code and token are not at fault.

**How to apply:** when collection is stale, run `gh run list -R thejoycething-code/citizengo-meta-reports` and read the job annotations (`gh api .../check-runs/<job id>/annotations`) before guessing. Keep long transcription batches off Actions minutes. gh lacks the `user` scope, so it can't read billing. Related: [[meta-organic-reports]], [[ig-video-transcription-feasibility]]
