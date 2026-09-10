---
name: x-source-groundwork
description: "X (Twitter) data source for the Meta reporting connector — scoped 8 Sep 2026, groundwork committed dormant on branch x-source, not pushed; go-live checklist in README"
metadata: 
  node_type: memory
  type: project
  originSessionId: e2af6ace-e75c-4edc-ba39-9fc74d2b295c
  modified: 2026-09-08T13:51:50.568Z
---

Scoped 8 Sep 2026 for Marisi Moreno (Asana task 1218268802872745, due 20 Sep
2026). Brief for Frida Espinosa and Marisi: Google Doc "X data via MCP – scoping
brief" (id 18tsvtA34AHHxBX08DJChEvb9a80WBpts4Fj2K5sC4yk), private to Chris until
shared. Nothing posted to Asana yet; a draft comment was prepared.

**Verified against docs.x.com, 8 Sep 2026:** private metrics (link clicks,
profile clicks, organic/promoted) only for own posts under 30 days, no backfill;
public metrics no window, 3,200 posts deep. Pricing per resource returned:
$0.001 own post, $0.005 other, $0.010 user lookup, deduped per UTC day. The two
"disputed" prices were both right — different line items. Scraping and resellers
ruled out by the developer terms. NOT yet verified live: `npm run probe:x` is
that check and comes before anything else.

**Groundwork state:** branch `x-source` in
`~/Desktop/Claude Code Projects/Meta Reports`, one commit, **not pushed**, not
merged. Everything dormant: schema in `sql/x-schema.sql` unapplied (preflight
treats x_* as PENDING), workflow `x-collect.yml` skipped unless repo var
`X_COLLECT_ENABLED=true`, tools hidden unless `X_TOOLS_ENABLED=true`, endpoints
503 until `X_*` env exists. 67 tests in `scripts/test-x.js`. Go-live checklist
is the README section "X (Twitter) source".

**Decisions baked in, and why:**
- Same connector as Meta, not a second one — one token, cross-platform questions.
- Schedule 7 daily reads + 1 final read at day 26-29 (`lib/xschedule.js`):
  $31-67/month for 30 accounts at 3-8 posts/day vs $90-225 re-reading the window daily.
- Refresh tokens ROTATE, so they cannot be GitHub secrets. They sit in
  `x_oauth_tokens` sealed to a public key; Vercel holds only the public key,
  the collector only the private (`lib/xauth.js`). `npm run x:keygen` once.
- Budget guard: collector refuses to start past `X_MONTHLY_BUDGET_USD` (100).
- Spokesperson accounts: only posts carrying a CitizenGO link are stored.
  That is a commitment made in the brief; it lives in schema, collector, tools.
- Collector assumes X refuses private groups on old posts as PARTIAL errors.
  If the probe shows the whole request fails instead, `collector/x.js` needs changing.

**Open questions for Marisi/Ignacio:** existing X developer account (Ignacio
"uses the X API", Jul 2026)? who funds credits? country accounts only or
spokesperson personal accounts too (Sebastian Lukomski, Rocío D'Angelo — consent)?

**How to apply:** do not push or merge `x-source` without being asked. Start
go-live at the probe, not the schema. See [[meta-organic-reports]],
[[meta-mcp-security-posture]], [[meta-silent-failure-pattern]].
