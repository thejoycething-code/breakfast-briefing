---
name: meta-who-shared-not-available
description: Meta will not say WHO shared a post — sharedposts and reactions return empty even on a post shared 10,764 times; commenters and counts are available
metadata:
  type: project
---

**Sharer identity is not obtainable.** Probed live on Graph v23.0, 23 Sept 2026 (`scripts/probe-who-shared.js`, in the "Probe metric coverage" workflow) against our four most-shared posts — the largest shared **10,764 times**:

- `/{post-id}/sharedposts` — **0 rows**, with and without a `fields` list
- `sharedposts` as a nested field — the response comes back carrying only `id`, no `sharedposts` key at all
- `/{post-id}/reactions` — **0 rows**. Who *reacted* is withheld too

An empty edge on a post shared ten thousand times is Meta declining, not us asking wrongly. There is no page or influencer list to be had, and no amount of permission changes it — this is the product, not our token.

**What IS available:**
- `/{post-id}/comments` returns rows with comment ids and message text, so *commenter* identity is reachable where sharer identity is not.
- `post_activity_by_action_type` insights gives lifetime counts (`share`, `like`, `comment`). Note its share count differs slightly from `shares_total` — 10,428 against 10,764 on the same post — so the two are not interchangeable.

**How to apply:** when someone asks which pages or influencers amplified us, the answer is that Meta does not publish it, and say so rather than reaching for a proxy. The nearest honest substitutes we already hold are `meta_post_amplification` (reactions on reshares against reactions on the post, which measures the *effect* of sharing without naming anyone) and the comment stream. Related: [[meta-organic-reports]], [[ig-video-transcription-feasibility]].
