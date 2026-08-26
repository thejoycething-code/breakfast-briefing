---
name: briefing-markup-becomes-testcase
description: "Chris's briefing corrections go into testcases.txt as a failing case BEFORE any pattern is edited — never a silent regex tweak"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a57d7dd3-e523-436d-a840-f273f2ef0d86
  modified: 2026-08-18T21:05:12.187Z
---

Every correction Chris makes on a Breakfast Briefing edition must be written into
`~/Downloads/breakfast-briefing/testcases.txt` as a case that FAILS first, then the rule is
changed until it passes. His words: "Can you ensure my markups do become test cases, not regex
edits." Run `python3 run_tests.py` before and after every pattern change.

**Why:** the pipeline was verified ad hoc for weeks — a check by hand, the check scrolls away,
the next change has no memory of it. That produced eight substring collisions of one family
(oman/Woman, WHO/who, telegraph/telegraphindia, herald/Deccan, express/Indian Express,
the federal/The Federalist, assembly/NI Assembly, timor/Baltimore) and one latent suppression
bug. I wrote the timor/Baltimore collision an hour *after* building the fixture meant to catch
exactly that shape, which is the argument for the discipline rather than against it.

**How to apply:** open testcases.txt, add the case under a dated comment naming whose judgement
it encodes and quoting Chris where possible, watch it fail, then edit `shortlist.py` /
`regions.py` / `compose.py`. Assertion kinds: SECTION, REGION, SUPPRESS/KEEP, ABOVE (ranking),
OUTLET (display names). A correction he can't express as a case is a signal the pipeline has no
lever for it — say so rather than hand-fixing the edition.

**Ranking corrections specifically → ABOVE pairs** (established 18.08.2026, when the discipline
was extended from classification to scoring). "Story X ran too low" becomes
`ABOVE | X's headline | the headline that wrongly outranked it`, failing first. ABOVE pairs are
scored on headline vocabulary alone — no corroboration — so they encode the
said-versus-happened, scale and commentary axes, not day-relative size. Guard cases matter as
much as fix cases: when widening OUTCOME for "legalises", a paired case asserted that "an open
letter against legalising" must NOT gain the bonus. See [[breakfast-briefing]],
[[briefing-silent-suppression]], [[briefing-cluster-provenance]].
