---
name: parl-monitor-mcp-deferred
description: MCP access to parl-monitor was scoped 27 Sept 2026 and deferred; it stays an app for now
metadata:
  node_type: memory
  type: project
  originSessionId: 404725ef-add2-49ff-99ed-6d0902560495
  modified: 2026-09-27T22:40:32.456Z
---

On 2026-09-27 Christopher asked whether MCP functionality could be added to parl-monitor once the backfills ([[parl-monitor-backfill-2010]]) finish. After seeing the options, he chose to **keep it as an app for now**. Nothing was built.

**Why:** no reason was given beyond "for now". Treat it as deferred, not rejected.

**How to apply:** don't start MCP work unless he asks. If he does, the scoped plan was:
* a **separate connector** from the Meta one ([[meta-mcp-security-posture]]), because stances, 5CA verdicts and judge placements are internal judgements
* a **Postgres copy of queryable tables** written by a CI step after the store push, since the store is a release-asset SQLite file ([[parl-monitor-store-artifact]]). Bundling the SQLite into a Vercel deploy was ruled out because of its size and because connector deploys are CLI-only ([[meta-connector-deploy-is-cli-only]])
* **check the size after the backfill** against Supabase's free tier
* **candidate tools:** mp_record, division, who_spoke, issue_timeline, week_ahead, bill_status, search_pqs, petitions, and a scope argument for EU/DE/CA
