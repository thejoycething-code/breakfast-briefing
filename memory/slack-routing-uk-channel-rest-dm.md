---
name: slack-routing-uk-channel-rest-dm
description: Slack destination rule — UK content to #campaigns-en-gb, everything else DMs Christopher
metadata:
  type: feedback
---

Anything I send to Slack on Christopher's behalf routes by jurisdiction:

- **UK** (Westminster, and the devolved legislatures) → channel **C9RH217PZ**,
  `#campaigns-en-gb`. This is where the Monday parliamentary monitor edition
  already posts.
- **Everything else** (EU, Germany, UN, and any other non-UK monitor output) →
  **DM to U05LJP0BT61**, Christopher, team T066M0LAJ. Never a shared channel.

Stated 24 Sept 2026 when a one-off EU plenary re-check routine was first wired
to the channel and then corrected.

**Why:** #campaigns-en-gb is a UK campaigning channel and its members do not
want EU or other-jurisdiction traffic in it. It also explains the standing "no
Slack" decision on the EU monitor (1 Sept 2026) — that was about the channel,
not about Slack, so a DM does not cross it.

**How to apply:** when wiring any Slack step, name the destination explicitly
and tell the sending agent not to fall back to a channel if the DM fails —
a tool that resolves a user ID loosely can otherwise drift into the team
channel. See [[parl-monitor-division-brief-and-spoke]] for the existing DM
brief that already uses this user ID, and [[parl-monitor-eu-monitor]].
