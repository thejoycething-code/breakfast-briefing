---
name: parl-monitor-edition-recess-shape
description: Top lines lead with what's actionable (recess note is its own field, rendered last and outside the cap); "What's on" renders in recess too — renamed from "Week ahead"
metadata:
  type: feedback
---

Two shape rules for the Westminster edition, both from Christopher on
24 September 2026 after reading edition 6.

**Top lines lead with what is ACTIONABLE, not recess.** The recess note is no
longer a top line inserted at position 0 — it is `Edition.recess_note`,
rendered LAST and OUTSIDE the six-line cap. It is still one line, not a
banner: the August decision against a recess banner or footer stands.

**Why:** inserted first, it pushed five live consultation deadlines down the
page. Outside the cap so a busy week cannot silently drop the fact that
nobody is sitting.

**"What's on" renders in BOTH modes**, directly under Top lines / Decisions.
It used to live in the sitting-week branch of `digest.render()` alone, so a
recess edition dropped the forward view entirely. Renamed from "Week ahead"
because in recess every row in it is weeks out, and a heading promising
*this* week misdescribes its own contents. Sub-blocks keep the old
distinction; the empty-state wording is mode-specific ("Neither House sits
this week…" vs "Nothing on our ground in the chamber this week").

**Why:** recess is when forward notice is worth MOST. Edition 6 held two
scored events in `further_ahead` and showed them to nobody, both after the
House returned on 12 October.

**How to apply:** when a section is suppressed by mode, measure what the
suppression actually hides before accepting it. A test asserting a section is
absent may be locking in the bug — `test_recess_renders_allowed_sections_only`
asserted "## Week ahead" was absent and had done since the section was built.

The German edition (`tools/de_monitor.py`) still heads its own block
"Week ahead" — deliberately untouched, not yet aligned.

Related: [[parl-monitor-week-ahead-table]], [[parl-monitor-decisions-block]],
[[parl-monitor-pq-answers-in-edition]].
