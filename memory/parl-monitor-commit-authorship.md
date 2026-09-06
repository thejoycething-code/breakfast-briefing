---
name: parl-monitor-commit-authorship
description: Which Claude model wrote which parl-monitor commits, and why the git author line never tells you
metadata:
  type: project
---

Every Claude commit on parl-monitor carries **Christopher's** git identity in
the author AND committer fields, because those come from local
`user.name`/`user.email`. The model appears ONLY in the trailer:
`Co-Authored-By: Claude <model> <noreply@anthropic.com>`. Read the trailer,
not the author line — as of 2026-08-28 the history is **127 commits by Fable
5, 56 by Opus 5**, and every one of them says "Christopher Joyce" on top.

**Checked 2026-08-28** because I could not account for `36df6f3` ("Condense
the row furniture"): it carried Christopher's identity and I had not written
it. It is Fable 5's. So is the whole public-votes-page arc from 25 August —
bill cards, public verdicts, the per-party whip rule, service history,
shareable quotes, the profile hero, party marks, the journey collapse, the
card-housing build and its revert (`12ca807` / `6de9de5`).

To check any commit:

    git log -1 --format=%B <sha> | grep Co-Authored-By

**The lesson that cost something.** I had attributed the `tee`-without-
pipefail slip and four test-anchor mistakes to myself as errors I was
repeating, and told Christopher so. They are Fable 5's commits. The failure
patterns in this codebase are real and worth guarding against; they are not
one model repeating itself, and I should not narrate them as my own history
without checking the trailer first.

Unsigned commits are machine-made: the workflow's "Monday publish" commits,
plus merge commits like `ce507fd`.

Related: [[parl-monitor-build]], [[parl-monitor-deferred]],
[[parl-monitor-repo-access]].
