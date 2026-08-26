---
name: briefing-silent-suppression
description: A filter that hides items without printing them will eventually delete real news unnoticed — always list what was discarded
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 84d457ef-6b54-4c7b-8bd0-1fe284f8e407
  modified: 2026-08-13T07:29:12.808Z
---

Any filter in the Breakfast Briefing pipeline that removes items must print what it
removed. Chaff suppression was the one place an item could vanish with no trace, and on
13.08.2026 it was quietly deleting real news: `slams` — an ordinary political verb — killed
a Swedish abortion-vs-deportation bill and a Tamil Nadu Speaker's abortion remarks;
`casting` matched "broadcasting"; `olympic` killed a women's-category policy story; `scam`
killed an FBI marriage-fraud prosecution.

**Why:** Chris flagged seven stories he would have included and five were already in the
sweep — the system had them and discarded or buried them. Invisible discards cannot be
audited, so the bug survived weeks of daily runs. An `--show-chaff` flag was no defence:
nobody passes it.

**How to apply:** Two rules. Print discards by default, never behind a flag. And make
suppression rules rescuable — an item carrying a genuine issue signal (`CHAFF_RESCUE`) is
never dropped, however much showbiz vocabulary the headline contains. Reserve unconditional
suppression (`CHAFF_HARD`) for formats where the format itself disqualifies: listings,
broadcast schedules, devotionals. I repeated this exact mistake within minutes of fixing it
by blanket-banning People.com, which had covered two of the stories Chris wanted — so
outlet-level bans need the same rescue gate as word-level ones.

Related: [[breakfast-briefing]], [[briefing-ranking-single-pass]]
