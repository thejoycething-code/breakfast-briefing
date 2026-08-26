---
name: parl-monitor-repo-access
description: parl-monitor is private under thejoycething-code; never suggest adding the work account
metadata: 
  node_type: memory
  type: feedback
  originSessionId: af1747a8-8e00-46d5-a914-8de61a0b04db
  modified: 2026-08-21T13:28:26.978Z
---

The `parl-monitor` repo is private under the personal `thejoycething-code`
GitHub account. Christopher's CitizenGO work account must NOT be added as a
collaborator — he declined this explicitly (2026-08-21) when a commit link
404'd from a browser logged into the work account.

**Why:** the personal/work separation on this repo is deliberate. A 404 on a
commit link means wrong login, not a broken push — GitHub serves 404 (not 403)
for private repos the viewer cannot see.

**How to apply:** never propose collaborator changes or repo visibility
changes for parl-monitor. If a link 404s, point at the login, and verify the
push with `git ls-remote` instead of the web. See [[parl-monitor-build]].
