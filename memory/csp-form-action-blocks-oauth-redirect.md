---
name: csp-form-action-blocks-oauth-redirect
description: Chromium applies CSP form-action to the 302 a form POST returns, so a consent page with form-action 'self' silently strands the OAuth redirect; curl, Firefox and the test suite all pass
metadata:
  type: project
---

On the Meta connector's consent page, `Content-Security-Policy: form-action 'self'` (added 30 Aug 2026 in the anti-framing fix a44af91) made Chrome and the Claude desktop app refuse to follow the 302 to `https://claude.ai/api/mcp/auth_callback` after a successful token submission. The server logged 302 after 302, the user saw a blank page, and Claude never called `/api/oauth/token`. Found 3 Sep 2026 only because auth became mandatory and someone actually clicked through. Same day, `Referrer-Policy: no-referrer` on the same page made the browser send `Origin: null` on its own form POST, which the new Origin check refused — two hardening headers, each correct alone, each breaking the flow.

**Why:** Three independent probes said the endpoint was fine — curl follows any redirect, Firefox ignores form-action on redirects, and the suite asserts headers rather than driving a browser. Only a Chromium click-through shows it.

**How to apply:** Any change to the consent page's security headers must be verified in the Browser pane: load the live authorize URL, submit a token, and confirm the tab lands on claude.ai (the JSON runtime log then shows a `POST /api/oauth/token`). form-action must list exactly the redirect allowlist (`REDIRECT_ORIGINS` + claude.ai + loopback), never 'self' alone; referrer policy must be `same-origin`, never `no-referrer`. Related: [[vercel-env-pull-placeholders]], [[meta-mcp-security-posture]].
