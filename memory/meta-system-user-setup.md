---
name: meta-system-user-setup
description: Creating a Meta System User token has four ordered steps; two are skippable and fail confusingly. Proven 20 Aug 2026.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3623f219-565e-4661-80fa-999736b1e7f4
  modified: 2026-08-20T13:56:26.206Z
---

Getting a working Meta System User token (for [[meta-organic-reports]], repeated
once per Business Portfolio) needs four steps in this order:

1. App must be in the business — Business Settings → Accounts → Apps. Apps created
   under a personal developer account are absent; add by App ID as an app admin.
2. System User needs a role **on the app** — Assign Assets → Apps → **Develop app**.
3. System User needs the Pages — Assign Assets → Pages → **View Performance**.
4. Generate New Token → expiry **Never** → tick the scopes.

**Why:** steps 2 and 3 are both easy to skip and neither error names its cause.
Skipping 2 gives *"No permissions available — assign an app role to the system
user"* in the token wizard, because in Business Manager the app is an asset like a
Page. Skipping 3 gives a token that authenticates perfectly and returns zero pages.
Expiry defaults to 60 days in the newer UI, which would kill a nightly job silently.

**How to apply:** `Session has expired` in any automated run means a short-lived
Graph API Explorer token was pasted in — only user tokens carry a session, System
User tokens never produce it. Scopes to tick: `pages_show_list`,
`pages_read_engagement`, `read_insights`, `pages_read_user_content`,
`instagram_basic`, `instagram_manage_insights`. None need App Review for your own
pages; tick all six at once since regenerating to add one is a faff, and the token
is shown only once.
