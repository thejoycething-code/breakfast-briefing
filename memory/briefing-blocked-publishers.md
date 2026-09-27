---
name: briefing-blocked-publishers
description: "Church Times + EWTN GB behind Cloudflare challenge, Telegraph behind Tollbit 402; Bing single-term searches carry standfirsts"
metadata:
  node_type: memory
  type: project
  originSessionId: 21b59139-633e-4145-968c-96936ff4039b
  modified: 2026-09-27T00:27:47.315Z
---

As of 27.09.2026: churchtimes.co.uk (RSS, jobs feed, articles) and ewtn.co.uk (every path incl. robots.txt) answer a Cloudflare bot challenge (403 "Just a moment..."); telegraph.co.uk answers 402 (Tollbit pay-per-crawl). None of these are to be bypassed.

Legitimate routes in use: Google News for headlines; **Bing News RSS carries the publisher's own standfirst** but only answers ONE term per query (an OR-query returns ~1 result), so extra_feeds.txt has 13 `bingf ... kw:site:telegraph.co.uk <term>` lines, and EWTN GB now arrives via gnews+bing (its dead feed is commented out). fetch_feeds' dedup keeps the longer summary across duplicate copies. Telegraph leads with readable text: 43% (25.09) -> 61% (test 27.09).

**Church Times fixed 27.09.2026 via Feedly:** `feedly | ... | https://www.churchtimes.co.uk/rss` reads Feedly's public stream of the publisher's own RSS (40/40 items with 250-char standfirsts). Uses `$BB_FEEDLY_TOKEN` if set, else the unauthenticated endpoint — a ToS question for Chris. check_sources treats a feedly feed as healthy only if it has items from the last 3 days (Feedly serves stale items forever: EWTN GB's copy stopped 05.08.2026, so Feedly does NOT help EWTN).

**How to apply:** never use Feedly or any mirror to get past the Telegraph's Tollbit gate — that is a pay decision, not a block. Remaining human options: Feedly developer token, asking the Church Times to exempt /rss from its challenge, Tollbit licensing. See [[briefing-telegraph-100-cap]].

**Telegraph, 27.09.2026 evening:** Yahoo News republishes part of the Telegraph's output free under licence, with JSON-LD `provider: The Telegraph` and the Telegraph's own standfirst as `description`. `attach_syndicated_text` finds the copy via a Bing `site:yahoo.com` search, REQUIRES that provider credit (credited_description), and prints it as `> syndicated (...)`. 17 Telegraph leads got text that way on the test sweep. MSN also syndicates but serves an app shell with no credit to check — not used. The Telegraph's Bluesky (telegraph.co.uk) went quiet in June; AMP pages are 402 too.
