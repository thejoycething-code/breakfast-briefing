---
name: meta-page-vs-post-numbers
description: Business Suite views = page_media_view (includes ads); post-level sums are a different quantity; metric_date is off by one day
metadata:
  type: reference
---

**Business Suite "Views" is `page_media_view`.** Verified to the unit on two months for Citizen GO UK: July 1,700,950 and August 787,058, both matching the live API exactly. `page_summary` now leads with this figure.

**It includes ads.** The `is_from_ads` breakdown reconciles to 100% of the total: August 662,817 organic / 124,241 paid (15.8%); July 1,471,877 / 229,073 (13.5%). It also includes Reels, Stories and every other surface. Bonus finding: only 3.1% of August views came from followers.

**Post-level sums are a different quantity, not a disagreement.** Page level counts views that *occurred* in the window, any post age; post level sums *lifetime* views of posts *published* in it. July post-level (1,848,627) exceeds July page-level because July's posts kept earning views in August. Business Suite's "Interactions" is also narrower than `page_post_engagements`, which counts clicks — that mislabel is why the connector's engagement figure looked inflated.

**`metric_date` names the day the value DESCRIBES — re-dated 9 Sept 2026.** It used to be Meta's `end_time` date, which is the instant the day closed: always 07:00:00+0000, midnight Pacific, Meta's own account-day boundary and not the page's (probed on UK, Spain and Hungary pages — all 07:00+0000). Both collectors now subtract a day before storing, all 3,636 `meta_page_metrics` rows were shifted, and calendar filters are now read literally. **No reader should compensate any more** — `page_summary`'s +1 shift was removed. In `meta_ig_account_metrics` only `follower_count` and `reach` were shifted: the total_value columns and `followers_snapshot` are keyed to the collection date and must never be shifted with them.

Re-check with `scripts/probe-page-paid-split.js` (Actions → "Probe metric coverage", which takes page_id/since/until). Related: [[meta-organic-reports]], [[meta-followers-per-post]].
