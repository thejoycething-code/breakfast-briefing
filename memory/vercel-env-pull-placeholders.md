---
name: vercel-env-pull-placeholders
description: vercel env pull writes "[SENSITIVE]" for Secret-type variables, so it cannot validate a production secret; a pipe after a node check also swallows its exit code under set -e
metadata:
  type: project
---

`vercel env pull --environment=production` writes the literal `[SENSITIVE]` (11 chars) in place of every Secret-type variable (MCP_TOKENS, OAUTH_SIGNING_SECRET, SUPABASE_*). Only Config-type values come through. On 3 Sep 2026 a pre-deploy "is the configured MCP token strong enough to authenticate" check ran against those placeholders, concluded there were zero usable tokens, and its ABORT exit code was then lost because the node command was piped into `grep -v` — `set -e` only sees the pipeline's last status. The deploy proceeded on a false alarm.

**Why:** Turning authentication on with a token the guard rejects locks every user out. The env pull looked like the safe way to check first, and it silently is not.

**How to apply:** To confirm a production secret is usable, exercise it and read the runtime log: send a garbage bearer, then `vercel logs meta-organic-reporting.vercel.app` for ~25s — `lib/guard.js` prints `REJECTED a configured token` at point of use if MCP_TOKENS is weak; its absence alongside other log lines from the same window is the evidence. Never put a decisive node check in a pipeline; write its output to a file and test the status directly. Related: [[meta-mcp-security-posture]], [[meta-silent-failure-pattern]].
