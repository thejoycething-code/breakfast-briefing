---
name: briefing-telegraph-100-cap
description: "Telegraph reaches the sweep only via Google News, capped at 100 results; six topic-scoped queries added 24.09.2026; fetch KEYWORDS borrowed precise terms from the parl-monitor taxonomy"
metadata:
  node_type: memory
  type: project
  originSessionId: 776c60f8-1ff1-475a-a9cd-3ef847a485b1
  modified: 2026-09-24T07:58:49.124Z
---

The Telegraph's own RSS is behind Tollbit (HTTP 402, licensing, permanent). It reaches the sweep only via Bing (14 items) and a Google News site: search that returns at most 100 results, 88 of them from the last 36h, of a much larger daily output. On 24.09.2026 only 15 Telegraph items reached the sweep.

The fix on 24.09.2026 was six `gnewsf` topic queries in extra_feeds.txt, labelled "The Telegraph (life/gender/faith/speech/family/migration)". They took on-beat Telegraph items from 16 to 28. Google matches article bodies, so they return noise, and the keyword filter drops it (pinned by KEYWORD drop cases). The Doc credit comes from the publisher, not the label.

The same day, fetch_feeds KEYWORDS gained ~23 precise terms from ~/parl-monitor/config/taxonomy.yaml v1.8: Ofcom, dis/misinformation, small boats, grooming/rape gangs, online safety, human trafficking, modern slavery, Rwanda scheme, VAWG, Equality Act, two-child limit, and social media only with a regulatory noun. Measured: 8 of 1,862 dropped headlines recovered that day, all on-beat, no noise.

**Why:** Chris asked to check Telegraph coverage and to mine the parl-monitor taxonomy for terms.

**How to apply:** if one high-volume, feedless outlet looks thin, split its Google News query by topic rather than widening keywords. When borrowing taxonomy terms, use only phrases and proper nouns, never bare common words. Related: [[briefing-feed-depth-decision]], [[briefing-court-step-not-repeat]], [[taxonomy-v16-areas]].

**The Times (checked the same day), rejected:** it has no RSS, and its news sitemap would have taken on-beat items from 11 to 53. But thetimes.com/robots.txt has "User-agent: * / Disallow: /", it bars unlicensed use, and a device-verification check sits in front. So only the Google News search stays. The sitemap parser in parse_feed is kept for publishers that permit it. The sheet's preview fetcher still requests thetimes.com pages, which the Times disallows; I raised this with Chris. The Telegraph's robots.txt allows `*`.

**Times topic searches (added later on 24.09.2026):** the same six Google News topic queries, which query Google rather than thetimes.com, so they stay within its robots.txt. On-beat Times items went from 11 to 45 raw, and 33 reached the sheet after noise was removed. The noise is the job board, arriving as its own source "The Times Appointments" (blocked in extra_feeds and in BLOCKED_OUTLETS), and the notices pages (Births, marriages and deaths; Court Circular), which CHAFF_HARD matches with patterns anchored at the start of the headline.
