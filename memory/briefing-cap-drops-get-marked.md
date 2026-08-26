---
name: briefing-cap-drops-get-marked
description: "Cap-dropped stories are retired to cut.json and dropped from later sweeps, never flagged as published"
metadata: 
  node_type: memory
  type: project
  originSessionId: 56a31411-1c43-4503-ab50-1e5a9db75951
  modified: 2026-08-18T19:31:44.463Z
---

A pick that loses to a section cap is **retired, not published**: it goes to `cut.json` and
later sweeps drop it outright rather than keeping it with a `[ran]` flag.

Chris, 18.08.2026: "if they didn't make the first cut they're not good enough for the
following day's briefing." This does not weaken the 13.08 rule that a repeat is the curator's
choice — that rule is about stories which actually *ran*, and a running story can legitimately
continue. A story beaten by the cap has already had its quality judged.

**Why the plumbing changed:** `mark_published.py` marked picks.json, not what compose emitted,
so on 18.08.2026 it recorded 357 stories for a 333-item doc — stamping 24 cap-dropped items as
published. They were not lost (a seen story is kept and flagged, `fetch_feeds.py`), but they
carried a false `[ran]` date plus the ranking demotion at `shortlist.py` ("don't re-lead old
news"). Wrong either way: they should have been retired outright.

**How it works now:**
- `compose.py` writes `composed.json` = `{composed: {section: [idx]}, cut_by_cap: {...}}`.
  Indices, not URLs, because the resolver rewrites `item["url"]` in place.
- `mark_published.py` prefers that record over picks.json, so marking can never disagree with
  the cap. It refuses to run if composed.json is from a different run, and warns if absent.
- Cut items are written to `cut.json` *and* seen.json — if cut.json is lost the sweep degrades
  to flag-and-keep rather than silently offering them as fresh.
- `fetch_feeds.py` drops cut keys in the dedup loop and reports "N dropped as cut by an
  earlier cap" in the sweep header.

**How to apply:** over-pick freely for capped sections — the cap decides and the losers retire
themselves. Only the cap retires items; a repost-link drop or an out-of-range index does not,
since those are link problems rather than quality judgements. Related:
[[briefing-gnews-decode]], [[briefing-drive-upload-limit]].
