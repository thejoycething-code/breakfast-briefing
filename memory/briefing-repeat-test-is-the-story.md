---
name: briefing-repeat-test-is-the-story
description: A repeat is judged on the underlying story - same actors and event - not on the outlet or headline
metadata:
  type: feedback
---

Chris, 31.08.2026: "If it's the same lawmakers etc. it's the same and should be deduped."

The `[SAME STORY ran]` flag is judged on **the story, not the outlet or the wording**. Same
actors, same document, same event = the same story, dedupe it, however different the byline.
A specialist outlet being the better citation is an argument for picking it **first time**,
not for running the story again.

**Why this is written down:** I loosened this rule on 31.08.2026 on his initial reading that
Morning Star News' Pakistani-Christian-girl story was not a duplicate. Checked against the
archive, it was: same 11 lawmakers, same 20 August letter, run by Hindustan Times on 28.08.
So were the other two I "restored" — EWTN's DOJ/faith-leaders piece (same 27 Aug meeting, PR
Newswire, 28.08) and Newsweek's Florida vaccine-exemption story (Ars Technica, 27.08). He
corrected it himself and the loosening was reverted. Lesson: verify a repeat claim against
`archive/<day>/composed.json` before changing a rule on it — the archive answers it in
seconds and I had already built it for exactly this.

**The flag's real failure is the opposite direction:** headline-overlap clustering merges
DIFFERENT stories. On the same sweep it filed a Vietnamese pastor's 7-year sentence as the
same story as an Indonesian pastor's. That is what to override. See
[[briefing-clustering-two-purposes]] and [[briefing-relay-not-primary]].
