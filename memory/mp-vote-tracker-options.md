---
name: mp-vote-tracker-options
description: MP Vote Tracker — four grouping-layout HTML forks built for CitizenGO
metadata: 
  node_type: memory
  type: project
  originSessionId: e49c974b-5f52-4f9b-bc61-42afa9dd351d
---

CitizenGO MP Vote Tracker prototype. Source files in `/Users/chrisjoyce/Downloads/files/`:
base prototype `mp-vote-tracker.html` (self-contained, data inlined on one line ~246),
`dataset.json`, `pipeline.py` (regenerates data from UK Parliament APIs), `BRIEF.md`.

On 2026-07-19 built the four grouping layouts per BRIEF.md, each a fork of the base
changing ONLY how divisions are grouped/elevated in the MP card:
- `option-a-by-reading.html` — sub-head by stage_group (2R → Report → 3R), skip empty headers
- `option-b-key-vs-amendments.html` — landmark==true under "Key votes", rest in `<details>` collapsed
- `option-c-landmark-hero.html` — landmark hero strip + full record grouped by reading beneath
- `option-d-flat-sorted.html` — flat list, landmark-first then by date, stage as small tag

Non-obvious decisions: added `rowHTML`/`issueHeadHTML` shared helpers; render the issue
`note` and division `context` (base didn't) to satisfy the abortion transparency rule;
in Option C, skip the "Full record" block when every division is a landmark (avoids
showing the single abortion row twice). Generator script was in scratchpad (ephemeral).

All 5 BRIEF test-checklist items verified live via browser JS (Kim Leadbeater 8 divisions,
Sarah Pochin "Not yet an MP" for 29 Nov 2024 2R, abortion elevated with host bill as context).
See [[clacton-vercel-deployment]].
