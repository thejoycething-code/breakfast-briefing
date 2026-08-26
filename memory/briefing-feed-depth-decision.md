---
name: briefing-feed-depth-decision
description: "Feedly's API is Enterprise-only, and Chris decided on 13.08.2026 not to fix RSS feed-depth truncation for now"
metadata: 
  node_type: memory
  type: project
  originSessionId: 84d457ef-6b54-4c7b-8bd0-1fe284f8e407
  modified: 2026-08-13T13:23:57.625Z
---

Two settled decisions about the Breakfast Briefing's collection layer, so neither gets
re-litigated:

**Feedly's API is Enterprise-only.** Both the Feed API and the Search API moved behind
Enterprise (from roughly $1,600/month) — Pro no longer yields a developer token. Don't
propose the Feedly API again without new pricing information. A `feedly_source.py` was
written and deleted the same day.

**Feed-depth truncation is deliberately unfixed** (Chris, 13.08.2026: "let's not fix it at
all for now"). The audit measured feeds serving 10,114 items with only 2,991 inside the
36-hour window, because RSS feeds hold a fixed number of items and a once-daily sweep cannot
see what has already scrolled off. Recovering it needs something polling every few hours and
storing results, which needs an always-on host. Chris chose not to run infrastructure.

**Why that is reasonable:** the same day's prefilter repair took candidates from 737 to
1,264 with no new hardware, and the bulk of the truncated remainder is the Mail's rolling
output and local US TV — the least valuable part of the corpus.

**How to apply:** the briefing runs on the laptop and needs it awake at 06:30. If the
subject comes up again, the cheapest real fix is an accumulating rolling store keyed by
`fetch_feeds.url_key` on any always-on machine Chris already owns (residential IP matters —
datacenter ranges get blocked harder by the Telegraph, wng.org and Cloudflare-fronted
sites). `briefing-sources.opml` (287 feeds) and `audit_feeds.py` exist for that day.

Related: [[breakfast-briefing]], [[briefing-ranking-single-pass]]
