---
name: parl-monitor-decisions-block
description: "\"Decisions needed\" block under Top lines (7 Sept 2026): config/decisions.yaml holds decision/owner/decide_by; block counts down, shows decided for 14 days, and names unlogged \"open decision\" why-lines"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8990c34a-d7d3-45f9-8650-9c152f231f17
  modified: 2026-09-07T11:59:57.456Z
---

Christopher, 2026-09-07: "Build the decisions block." Built the same day.

**Shape.** `config/decisions.yaml` entries: id, decision (a question), about (a
phrase in the item TITLE used to pair it), owner (null = unassigned), decide_by,
opened, status open|decided, decided_on, outcome. `src/decisions.py`: `load`,
`collect(log, mentions, week)` → {open, decided, unlogged}, `render`. Rendered
directly under Top lines in both edition modes. `mentions` = (title, why) of
every rendered item plus the consultation rows; a why matching OPEN_PHRASE
("open decision", "undecided", "yet to decide", ...) with no `about` match is
listed as "not yet logged (needs an owner and a date)".

**Why:** the SEND reform why-line said "A supporter response is still an open
decision" for a second week; a why-line cannot carry owner or date, so it
recurred. Seeded with `send-eotas-response`, owner null, decide_by 2026-09-14
(drafted as four days before the 18 Sept close; Christopher to confirm).

**How to apply:** to close one, set status: decided, decided_on, outcome; it
shows for 14 days then drops. Never invent an owner: null renders as
*unassigned*, which is itself the prompt. See [[parl-monitor-build]],
[[uk-campaign-calendar]].
