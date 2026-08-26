---
name: api-spend-approval
description: "Always ask Christopher before spending Anthropic API funds, except the routine weekly pipeline tasks"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2fa51e3b-34ec-4638-9e48-df2232ac2520
  modified: 2026-08-06T04:29:27.706Z
---

Ask Christopher before any action that spends Anthropic API credit. The only
standing exception is the **usual weekly tasks**: the Sunday pull's triage
pass and its stance-scoring pass, which are budgeted, capped
(`stance_weekly_max_refs`, ~£1/month all in) and run unattended by design.

Everything else needs a heads-up with an estimate first: backfills,
re-scoring passes, one-off classification jobs, or anything that reprocesses
historic data.

**Why:** stated 2026-08-05 after the historic backlog ran to ~£30 across
several runs, part of it wasted on my own bug. He has a monthly usage cap set
in the console and wants to decide each discretionary spend himself rather
than discover it afterwards.

**How to apply:** say what the job is, how many refs or batches, and the
estimated cost, then wait. Related: [[parl-monitor-build]].
