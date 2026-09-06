---
name: briefing-relay-not-primary
description: A ★ source relaying a newsroom is not the primary source; it was suppressing six national reports
metadata:
  type: feedback
---

`PRIMARY_SOURCE` gave an unconditional cluster bump, so it fired even when an advocacy body
was merely **passing on** another outlet's reporting — and then suppressed that reporting.
On 31.08.2026 six newsrooms filed that Burnham would abstain on the assisted dying Bill
(Telegraph, Times, Independent ×2, Manchester Evening News, LBC) and all six collapsed under
SPUC's item, whose own summary opens *"According to Politics UK, Andy Burnham has told Labour
MPs…"*. The sheet prints one line per story, so only SPUC's was ever visible, and the edition
ran a Telegraph opinion column where its news report should have been. Chris added the news
report back by hand.

**Why:** the rule in [[briefing-cluster-provenance]] is right — ADF publishing a UN letter it
obtained IS the document and beats EWTN's write-up. The missing distinction is **issuing vs
relaying**. `relays_another_outlet()` now tests attribution in the item's own **feed summary**,
because clustering runs before `attach_openings` and the article text does not exist yet at
that point. The institution guard is the load-bearing half: "according to a new Government
assessment" is Right To Life reading a document (tier 1 the same day), not relaying a
newsroom.

**How to apply:** measured on the 31.08 sweep the change moves exactly **one** cluster leader
of 112 — it is surgical, not a re-ranking. Beware measuring this by recomputing
`max(cluster_rank)` over the members shortlist printed: that ignores `apply_cluster_preference`
and `DEDUPE_EXEMPT` and showed 15 spurious changes. Isolate by stubbing
`relays_another_outlet` to False and diffing.

A separate gap found the same day: `SOURCE_TIER` holds no mainstream national beyond the
Telegraph, Times and GB News, so **Advocate.com led a cluster of eight over the Washington
Post** on keyword score alone. "washington post" was appended (not inserted — his preference
order above it is untouched). Guardian, BBC, Sky, Independent and Mail are still absent and
that is Chris's call, not one to make silently.
