---
name: meta-connector-deploy-is-cli-only
description: The meta-organic-reporting Vercel project has no Git integration; pushing to GitHub deploys nothing, only `vercel --prod` does
metadata:
  type: project
---

The Vercel project `meta-organic-reporting` (org `team_rpnwoDBcJ5Wz1K5P8UCTGY2k`, `citizen-go-teammates`) is **not connected to the GitHub repo** `thejoycething-code/citizengo-meta-reports`. Pushing to `main` builds nothing. Every deployment in the project's history was made from the CLI by `cjoyce-7645`, and `vercel project inspect` lists no repository. Deploying is `vercel --prod --scope team_rpnwoDBcJ5Wz1K5P8UCTGY2k` from the project directory.

**Why:** I told Christopher on 21 Sept 2026 that a push would make a consent-page change live, then polled production for 4.5 minutes watching the old string come back. The commit was fine; the assumption that a git push deploys was not. Nothing in the repo says so either way — only the deployment list does.

**How to apply:** Separate "committed" from "live" when reporting on anything in this project, and verify against the production URL rather than the push. A CLI deploy ships the **local working directory**, not the pushed commit, so confirm `git status` is clean first or you will quietly ship something that was never reviewed. Live consent page: `https://meta-organic-reporting.vercel.app/api/oauth/authorize`. Related: [[meta-organic-reports]], [[vercel-env-pull-placeholders]], [[csp-form-action-blocks-oauth-redirect]].

**The session's own connector is not a deploy check.** On 21 Sept 2026 I deployed, called `mcp__citizengo-meta__search_posts` in the same session, saw the OLD output, concluded the deploy had not taken, and force-redeployed. It had taken — both times. A direct `POST /api/mcp` to `https://meta-organic-reporting.vercel.app` with a freshly minted token returned the new columns immediately. The connector already attached to a Claude session serves stale responses after a redeploy.

**How to apply:** verify a connector deploy by calling the production URL over HTTP, never by calling the connector tools loaded in the current session. Mint a throwaway token (`npm run tokens -- add verify-deploy`), call, then revoke it — the whole check takes one command each way.

