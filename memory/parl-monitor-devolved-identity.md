---
name: parl-monitor-devolved-identity
description: Wales keys votes by Senedd number and members by publicwhip URI; the name bridge lives in src/devolved.py and both scorer and page must use it
metadata:
  type: project
---

The Welsh record uses TWO id spaces that share nothing: `sd_votes.member_id`
holds the Senedd's own member number (1, 143, 145) and `sd_members.person_id`
holds publicwhip URIs. The only bridge is the member's NAME, and it lives in
`src/devolved.py` — used by BOTH `tools/devolved_score.py` (writing
`sd_scored.person_id`) and `tools/make_devolved_votes.py` (reading it). When
they disagreed, every verdict lookup missed and nothing looked broken,
because no Welsh division is signed off yet.

**Why:** identity mismatches here fail silently — the page builds, counts look
plausible, and votes belong to nobody (1,036 of them, first build). NI failed
the same way joining `event_id` where votes are stored under `doc_id`.

**How to apply:** never join Welsh votes on an id. Resolve names through
`devolved.roster()` — which reads `sd_members` PLUS the `member_aliases`
table, populated by `tools/sd_members.py` from parlparse's own Main and
Alternate names. Two traps are already paid for: parlparse puts a peer's
surname in `lordname`, not `family_name` (the First Minister sat in the
roster as "Mair Eluned" and matched nothing), and punctuation must be
deleted rather than spaced or "Andrew R.T. Davies" and "Andrew RT Davies"
become two people. Where the chamber and roster differ on middle names, one
narrow rule applies: identical surname, one name's words inside the other's,
and exactly ONE candidate — two candidates is unresolved, never guessed.
128 of 130 voter names now resolve; the two left are "Casting Vote" and the
Llywydd, neither a person. See [[parl-monitor-lords-inversion]] for the
sibling rule on what a division MEANS, and
[[parl-monitor-everyone-who-voted]] for who gets listed.
