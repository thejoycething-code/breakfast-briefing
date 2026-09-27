---
name: briefing-repo-is-public
description: thejoycething-code/breakfast-briefing is a PUBLIC repo but tracks memory/ and task/SKILL.md; never push a sync_docs commit without asking
metadata:
  node_type: memory
  type: project
  originSessionId: fa2fe69d-1670-4f71-88d9-ff98eeee523a
  modified: 2026-09-26T23:20:07.865Z
---

`thejoycething-code/breakfast-briefing` reports `visibility: PUBLIC` (checked 27.09.2026), yet `sync_docs.sh` copies all of memory/ and SKILL.md into it and the pre-commit hook forces those syncs. 71 memory files were already public on branch docs/step6-plaintext-export-trap before this was noticed.

On 27.09.2026 Chris chose to push code only: memory sync commit 03c7770 was reordered to sit after the code and kept local; origin is at 27498b3.

**Why:** memory holds unannounced campaign plans, Sheet IDs, internal routing and the user's email address. Pushing a sync publishes them.

**How to apply:** before any push in breakfast-briefing, run `gh repo view --json visibility`. If it is still public, push only commits that don't touch memory/ or task/ (`git push origin <sha>:refs/heads/<branch>`) and ask about the rest. Making the repo private is the user's call, not mine. Related: [[breakfast-briefing]], [[briefing-finish-edition-tail]].

**27.09.2026 late: Chris approved the memory push** (PR #2, 44 files). **meta-organic-reports.md is local-only by his decision**: it holds the connector's staff access-token roster. It is listed in `LOCAL_ONLY` in sync_docs.sh, so pull skips it and check ignores it, and it is untracked on main. Add any future file with staff or private personal data to LOCAL_ONLY the same way. The Clacton candidate's personal email was removed from clacton-vercel-deployment.md at his request, but it is still in git history before that commit. Local-only commit 03c7770 (branch docs/step6-plaintext-export-trap) contains the roster: never push it.
