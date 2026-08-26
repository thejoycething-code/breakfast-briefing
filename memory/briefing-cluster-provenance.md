---
name: briefing-cluster-provenance
description: "Inside a duplicate cluster, rank on provenance not news value — and ADF always beats EWTN"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 94c9330d-09f8-49b5-9d3c-ddff9199b4fc
  modified: 2026-08-14T07:59:13.591Z
---

In the Breakfast Briefing shortlist, choosing between members of a duplicate cluster is a
**provenance** decision, never a news-value one. `ACTION_BUMP` must stay out of it, and ADF
International always outranks EWTN.

**Why:** on 14.08.2026 the briefing credited EWTN's write-up of a UN letter to Nigeria instead of
ADF International's own release, which is the body that obtained and published the letter. Both
scored base 5 and both are in `SOURCE_TIER` (+6); the whole 3-point gap was `ACTION_BUMP`, because
the `ACTION` regex matches the active verb "warns" (EWTN) but not the noun "Warning" or the verb
"Release" (ADF). Advocacy bodies title their releases in nouns and newsrooms use active verbs, so
the bias was systematic — it would keep demoting exactly the primary sources Chris wants cited
(ADF, SPUC, ICC, Sex Matters, Right To Life). `ACTION_BUMP` is for ranking *different* stories;
every member of a cluster is the *same* story, so using it there is a category error.

**How to apply:** `cluster_duplicates()` sorts by `cluster_rank()`, not `rank_score()`.
`cluster_rank` returns a **tuple**, so a cosmetic signal can never outrank a real one — an additive
version was tried first and was worse, a +2 "direct link" bump beat `TIER_BUMP` and handed 11 of 78
clusters to untiered aggregators while promoting two stories that had already run. Precedence:
primary source → cited outlet → not already published → position in `SOURCE_TIER` → direct link
over unresolved redirect → keyword score. The ADF/EWTN rule lives in `CLUSTER_PREFER` and is
applied by `apply_cluster_preference()` **per cluster**, not as a score bump — a global penalty
would demote EWTN in the many clusters containing no ADF item, where EWTN is the right lead.

Two list gaps this surfaced, both now filled: `SOURCE_TIER` was missing Baptist Press (and Catholic
Review, Catholic Sun, The Pillar, ZENIT); `PRIMARY_SOURCE` now includes adversarial filers (ACLU,
Liberty Counsel, Becket) because on a suit they filed, their filing is the primary document and
provenance is not an ideological judgement.

Net effect on the 14.08 sweep: 11 of 78 cluster leads changed, `[ran]` leads fell 2 → 1. There is a
seven-case regression test in the session log covering ADF>EWTN, the two 12.08 pairs (Catholic
Herald>OSV, Telegraph>GB News), already-published, tiered>untiered, link quality and
primary>newsroom; it must pass in **both** feed orders, since ties used to be decided by luck.
See [[breakfast-briefing]] and [[briefing-ranking-single-pass]].
