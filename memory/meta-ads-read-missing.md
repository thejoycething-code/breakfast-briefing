---
name: meta-ads-read-missing
description: Ad spend stopped 29 Aug 2026 because the token lacks ads_read; no endpoint change can fix it
metadata:
  type: project
---

**`meta_post_ad_spend` has collected nothing since 29 Aug 2026.** Every nightly run is green; `adspend.js` logs `ad spend: unavailable ((#100) Unsupported get request)` from its first call, `/me/adaccounts`, and deliberately does not fail the run.

**Cause, established by `scripts/probe-adaccounts.js` (Actions → "Probe metric coverage") on 15 Sept 2026:** the token is a USER token — `/me` resolves to Ignacio Arsuaga — and `/me/permissions` lists seven granted scopes: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`, `pages_read_user_content`, `pages_show_list`, `public_profile`, `read_insights`. **`ads_read` is not among them**, nor `ads_management` or `business_management`. So `/me/adaccounts`, `/me/businesses` and `/me/assigned_ad_accounts` all fail on permission.

**How to apply:** This is a re-authorisation task, not a code fix — do not swap the endpoint, every route fails the same way. The token must be re-granted `ads_read` (and `business_management` if business-scoped enumeration is ever wanted). Until then `ad_spend` serves August data; `data_health` now states its age and that collection is otherwise green. Re-run the probe after any re-auth to confirm the scope actually landed. Related: [[meta-organic-reports]], [[meta-silent-failure-pattern]].
