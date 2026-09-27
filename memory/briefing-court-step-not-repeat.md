---
name: briefing-court-step-not-repeat
description: A hearing/ruling in a running fight is a new event; ran_before now splits hearing headlines; fragmented x1 lines hide a big story
metadata:
  node_type: memory
  type: feedback
  originSessionId: 776c60f8-1ff1-475a-a9cd-3ef847a485b1
  modified: 2026-09-24T06:36:10.332Z
---

A new step in a running fight (filing, hearing, ruling, appeal, vote, sentencing) is new news, not a repeat. Judge the flag by what HAPPENED in the item, not what it is about.

**Why:** 24.09.2026 markup: the White House media-ban hearing arrived as ~15 separate x1/x2 lines, several flagged SAME STORY against the ban's 21–22.09 announcement. I accepted the flags and it never ran; Chris named WaPo's "shaky ground" piece as a miss. Same markup: the Economist's China-censorship piece was read past (my judgement), WORLD's US-warns-Australia story sat in NO SECTION MATCHED ("digital safety legislation" matched nothing), the Hill's news feed holds only its latest 15 items so its version was gone by the sweep, and the Herald's news desk was never swept.

**How to apply:** `COURT_HEARD` in shortlist.py (used by `ran_before` only) splits hearing headlines from non-hearing ones. Non-hearing court steps ("DOJ defends ban…") still get flagged, so check them by hand. Fifteen lines on one subject means a big story that failed to cluster. Fixes shipped 24.09: Free Speech gained digital-safety and social-media-law vocabulary; the Herald's /news/rss/ and /politics/rss/ feeds were added; a "Hill (speech watch)" gnewsf query was added. Related: [[briefing-repeat-test-is-the-story]], [[briefing-suppression-two-buckets]], [[briefing-feed-depth-decision]], [[briefing-markup-becomes-testcase]].
