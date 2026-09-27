---
name: meta-graph-error-1-deterministic
description: "Graph error #1 \"reduce the amount of data\" is deterministic, not a throttle; halve the page size instead of retrying"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9359249e-53a6-45e4-92a0-7d6359a81ae2
  modified: 2026-09-07T17:58:47.002Z
---

Meta Graph error `#1 "Please reduce the amount of data you're asking for, then retry your request"` is **deterministic**, despite the wording telling you to retry. CitizenGO Magyarország (page 773710406017012) failed on its first `/published_posts` call in the 90-day backfill, then failed again ten seconds into a lone retry at concurrency 2 — identical error. The cause is request weight, not rate: `POST_FIELDS` asks for `attachments{...}` and `shares` on 100 posts at a time, and some pages carry far more attachment data per post. Halving to `limit=50` collected all 224 posts.

**Why:** "then retry your request" reads exactly like a throttle, so the instinct is to wait and retry, or lower concurrency. Both fail forever. The fix is a smaller request, not a calmer one. `listPosts` in `collector/collect.js` now halves the page size on `#1` down to a floor of 10, leaving the cursor untouched so it resumes rather than restarting.

**How to apply:** When a Meta call fails twice with the same error and the same call count, stop retrying and change the request shape. Distinguish it from real throttling by whether a lone low-concurrency retry also fails — if it does, it was never load. Say so rather than looping. Related: [[meta-silent-failure-pattern]], [[meta-organic-reports]].
