---
name: briefing-common-word-clusters
description: A big xN on a vague topic phrase is a bogus cluster; words_overlap_enough needs 1 uncommon shared word
metadata:
  node_type: memory
  type: feedback
  originSessionId: fe309bc6-d989-4401-8273-0686b3db95b2
  modified: 2026-09-23T11:38:27.691Z
---

On 23.09.2026 Chris flagged 9 missed stories. The worst: corroborate() built an "x19" cluster anchored on First Liberty's 3-word "Reflecting on Religious Freedom". Every "religious freedom" headline matched it 2/3, so 18 unrelated stories (Christianity Today on Cissie Graham Lynch/IRF, Trump appointing a jailed pastor to USCIRF, Yom Kippur threats) never reached the sheet. The printed lead borrowed First Liberty sibling text about the Founders, which was the tell.

Fix: shortlist.words_overlap_enough(), shared by corroborate() and same_story(). A word-overlap merge needs at least COMMON_MIN_DISTINCT=1 shared word used by fewer than max(15, 1.2%) of the day's headlines. It is guarded by test_common_words_do_not_cluster. rank_eval went 0.639 to 0.643. Setting it to 2 broke genuine clusters.

Same day: added Irish Times politics and Yorkshire Post opinion feeds to extra_feeds.txt. Local News Matters' abortion-pill-reversal story was lost because I parked it at tier 3 and the US cap cut it.

**Why:** a high xN on a generic phrase, with sibling text that doesn't match the headline, means a bogus cluster, not a big story.
**How to apply:** when reading the sheet, sanity-check any x10+ lead whose headline is generic. Tier 2 anything I'd be sorry to lose (see [[briefing-cap-drops-get-marked]]).
