---
name: meta-followers-per-post
description: Followers per post collected for Instagram FEED only since 7 Sept 2026; Facebook has none; null means not offered, not zero
metadata: 
  node_type: memory
  type: project
  originSessionId: 9359249e-53a6-45e4-92a0-7d6359a81ae2
  modified: 2026-09-07T15:48:28.277Z
---

Followers gained per post: **Instagram FEED yes, Instagram REELS no, Facebook no.** Probed live on Graph v23.0 on 7 Sept 2026 by `scripts/probe-follower-metrics.js` (Actions → "Probe follower metrics"). A FEED post returned `follows=3`, `profile_visits=46`, `profile_activity=39`; a REELS post from the same account rejected all three with "does not support ... for this media product type". Facebook rejected five candidate names while controls passed, so the metric is absent, not unpermitted. **Collected since 7 Sept 2026** into `meta_ig_media_metrics.follows / profile_visits / profile_activity`, exposed on the `meta_ig_latest` view and in the `instagram_posts` tool table (Follows / Avg watch columns, added 8 Sept 2026).

**Why:** We hold followers per page per day (`meta_page_metrics.daily_follows`) and it cannot be pushed down to posts: of 3,557 page-days with a non-zero change, only 16% had exactly one post and 67% had none, and the median absolute change is 0 either way. The signal is below the noise floor, so any per-post figure has to come from Meta or not exist.

**How to apply:** Quote these for IG FEED only and say so — a blended "followers per post" across FB and Reels would be mostly fabricated, and Reels are 374 of 790 posts. A null is "not offered for this product type"; a 0 is measured. The request is gated on `media_product_type = 'FEED'` in `IG_FEED_METRICS` (`collector/instagram.js`) rather than attempted-and-caught, so Reels record no error either. Nothing is backfilled before 7 Sept 2026 — older posts need a longer `lookback_days`. Re-run the probe whenever `GRAPH_VERSION` moves; the answer is version-specific. Related: [[meta-organic-reports]], [[meta-silent-failure-pattern]].
