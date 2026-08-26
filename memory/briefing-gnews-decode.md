---
name: briefing-gnews-decode
description: Google News redirects decode 100% via the batchexecute signature route; resolved.json must never cache failures
metadata: 
  node_type: memory
  type: project
  originSessionId: 56a31411-1c43-4503-ab50-1e5a9db75951
  modified: 2026-08-18T18:47:14.270Z
---

Google News redirects can be turned into real publisher URLs at a 100% rate (114/114 on the
18.08.2026 edition) by asking Google: fetch the redirect page, read its `data-n-a-sg`,
`data-n-a-ts` and `data-n-a-id`, POST them to
`news.google.com/_/DotsSplashUi/data/batchexecute`, read `garturlres` out of the reply.
Implemented as `resolve.decode_gnews()`, tried before slug-guessing.

**Why:** it is authoritative rather than constructed, so it beats guessing on the two cases
guessing can never win — hosts that refuse our fetch (wng.org, telegraph.co.uk, thetimes.com,
premierchristian.news, aei.org, liveaction.org) and URLs with opaque suffixes like
`wng.org/sift/<slug>-1786981243`, the exact shape Chris had to supply by hand on 13.08.2026.
What had genuinely died is the *older* trick of decoding the base64 in the URL; the signature
route is alive. resolve.py's docstring asserted the whole approach was dead — do not trust a
"this no longer works" comment without re-testing it.

**How to apply:** a decoded URL must NOT go through `confirms()`. Verification exists to catch
a guess, and it produces false negatives on legitimate URLs whose page title is a shorter
re-sub of the headline (organiser.org, 18.08.2026) — applying it would discard correct answers
for precisely the blocked hosts this route rescues. See [[briefing-markup-becomes-testcase]]
before touching the guess-and-verify fallback.

**`resolved.json` must only cache successes.** It used to store `None` for misses, which pins
a failure to that headline permanently: the decoder landed and changed nothing at first,
because all 81 of that morning's misses were already cached as failures and never retried.
381 of 524 entries were negative; purged. A cached miss silently freezes the resolver at
whatever it could do the first time it saw a story.
