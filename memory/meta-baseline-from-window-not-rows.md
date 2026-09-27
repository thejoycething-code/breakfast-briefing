---
name: meta-baseline-from-window-not-rows
description: top_posts measured "vs median" against the rows it displayed, not the window — a page baseline computed from the top N is the top N
metadata:
  type: project
---

`top_posts` computed its `pageBaseline()` from `feed.rows`, and **`shapeFeed` applies `limit` before it returns**. So the "page median" was the median of the handful of posts on screen — the biggest ones. HazteOir's 90-day median read **1,090,875 views at `limit=5` against a true 25,757**: every "vs median" multiple on that page was measured against a bar roughly forty times too high, on the one column whose entire purpose is to say whether a post beat its page's normal.

Fixed 21 Sept 2026 by shaping once **without** `limit`, taking the baseline from that, then slicing for display. The other three callers of `pageBaseline` (`outliers`, `digest/build.js`, `scripts/status.js`) all pass unlimited rows and were never affected — only `top_posts` had it.

**Why:** the output looked completely reasonable. A median is a plausible-looking number whatever you feed it, and the comment above the call even said "Baseline from the same window" — the intent was right and the code took the top N. Nothing failed, nothing was null, no test covered it. It surfaced only because a median of 1.09M looked wrong next to a 420th-ranked post with 18k views.

**How to apply:** whenever a baseline, median, average or benchmark is computed in this codebase, check what set it is computed **over** versus what set is **shown** — they are different sets and the limit belongs only to the second. `scripts/test-top-posts.js` pins it by asserting the median does not move as `limit` changes; reintroducing the bug makes it drift 10,000 / 9,750 / 5,250, which is the signature to look for. Related: [[meta-silent-failure-pattern]], [[meta-organic-reports]].
