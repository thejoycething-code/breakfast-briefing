---
name: briefing-suppressed-rescues-lack-ran-flags
description: "Breakfast Briefing — the two SUPPRESSED blocks print no [ran]/[SAME STORY] flags, so rescues from them can be straight repeats"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f6096e0b-ba94-4152-aea8-747970a71c8a
  modified: 2026-09-04T05:09:29.511Z
---

The CHAFF and NO SECTION MATCHED blocks at the end of shortlist.py print only `index | headline | outlet` — **no `[ran MM-DD]` and no `[SAME STORY ran]` flag**, unlike every line in the sections and the ranking sheet. So a story rescued from those blocks arrives with no repeat history attached.

On 04.09.2026 that shipped two straight repeats out of 250: `399` (FoRB in Full, Sudan — same URL ran 09-03) and `1354` (The Spectator, "Texas was right to save baby Gabriel-Rumi" — same headline ran 09-02). Both were genuinely good rescues on the merits; neither showed it had already run. compose.py's own REPEAT report caught them, but only *after* publishing — it prints at compose time and finish_edition.sh does not gate on it.

**Why:** the suppressed blocks are the one place the brief actively tells you to pick from (`OTHER_ALLOW` is deliberately narrow, and real news dies there — the Farage by-election commentary, the A-level results), but they are also the one place with no repeat signal. The rescue instruction and the dedupe instruction don't meet.

**How to apply:** after choosing rescues from either SUPPRESSED block, grep each index's headline against the last few days' `archive/` or `seen.json` before adding it to picks.json — or at minimum read compose.py's REPEAT block *before* accepting the edition rather than after. Same discipline as the reclass list, which those rescues always trip anyway (they reached no section, so every one is a "mismatch" by construction).

Related: [[briefing-two-suppression-buckets]], [[briefing-repeat-test-is-the-story]], [[briefing-finish-edition-tail]]
