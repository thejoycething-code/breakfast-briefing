---
name: briefing-ranking-single-pass
description: Ranking the Breakfast Briefing in one pass costs ~26k tokens and beats a subagent fan-out; corroboration count is the free importance signal
metadata: 
  node_type: memory
  type: project
  originSessionId: 84d457ef-6b54-4c7b-8bd0-1fe284f8e407
  modified: 2026-08-13T12:11:53.232Z
---

Reading a whole day's Breakfast Briefing candidates in ONE pass (`shortlist.py --sheet`)
costs ~26k tokens for ~740 candidates. The 17-slice subagent fan-out it replaced cost
roughly 250-300k — almost all per-subagent scaffolding plus the review brief repeated
seventeen times. Headlines are cheap; scaffolding is not.

The single pass is also better, not just cheaper: slicing by section made cross-cluster
ranking impossible, because a reviewer holding only Life cannot know whether a Nigerian
court ruling outranks the fifth Trump piece. Ranking across the issue cluster is the job.

**Why:** Chris asked (13.08.2026) whether items could be read and ranked by importance
across the issue cluster without burning tokens. Measuring it inverted my own design — I
had built the fan-out on the assumption that ~850 items could not be read in one context.

**How to apply:** Default to one pass over everything. `xN` in the sheet is the
corroboration count — how many outlets filed on a story, computed globally and reused from
the existing duplicate-clustering code. It is the only free measure of how big a story is
and it works: the Medicaid gender-care ruling came in at x18 and led the day, where keyword
scoring had it mid-pack. Reach for a fan-out only when subagents must each do heavy
independent work (fetching and reading article bodies), never merely to read lists.

**Ranking model (`importance()` in shortlist.py).** Two insights carry most of the gain:

1. *Said versus happened.* The old scoring rated "Supreme Court strikes down the law" and
   "Campaigner slams the law" identically, because both contain "law". Outcome verbs get +8,
   process verbs ("urges", "warns", "slams") +3, commentary framings −2. A digest leads with
   outcomes; reaction fills the space beneath them.
2. *Corroboration must be weighted by outlet tier.* Raw counts measure general news bigness:
   an FBI visa-fraud sweep draws eight mainstream outlets while a Nigerian court freeing a
   Christian woman draws two movement outlets and matters far more here. Raw count is capped
   at +7; each corroborating outlet Chris actually reads adds +3.

Chris's rule on source concentration (13.08.2026): an outlet "can take more than three slots
if important" — so the per-outlet cap is a tie-break among ordinary items, never a ceiling
on good ones (`--outlet-exempt`, default 14).

Related: [[breakfast-briefing]], [[briefing-silent-suppression]]
