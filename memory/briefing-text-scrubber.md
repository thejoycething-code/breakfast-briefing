---
name: briefing-text-scrubber
description: "boilerplate.py strips site furniture at READ time; caches stay raw; learned per host, weekly relearn in eval_week.sh"
metadata:
  node_type: memory
  type: project
  originSessionId: 21b59139-633e-4145-968c-96936ff4039b
  modified: 2026-09-27T00:27:33.849Z
---

Since 27.09.2026 `boilerplate.py` scrubs article text before the sheet shows it (Independent login notice, GB News menu, EWTN/Newsweek blurbs, share bars). Three layers: a fixed LITERAL list, per-host 6-grams learned from the caches (`boilerplate.json`, `--learn`, rerun Saturdays by eval_week.sh), and day-level grams from the day's leads (Fox's in-body sidebar).

**Why:** on 25.09.2026 the "86% readable" figure counted menus as article text; 346/346 Independent and 232/232 GB News openings began with furniture.

**How to apply:** caches (openings.json, previews.json) keep RAW text — never scrub at fetch time or the learner loses what it learns from. Learned cuts need a run of ≥10 words (MIN_RUN) because ADF's recurring "the U.S. Court of Appeals for the" got learned; short furniture belongs in LITERAL. Scoped `(?-i:)` on "Comments" — the case-insensitive form ate "his comments". Opinion markers ("do not necessarily reflect") are never learned. A scrub change alters tiers.text_id, so the next --new-only sheet shows those leads once as changed. See [[briefing-text-for-judgement-only]].
