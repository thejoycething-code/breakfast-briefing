---
name: parl-monitor-ni-verdicts
description: NI decisions of 6 Sept 2026 — Amdt 97 (women's prison accommodation) and Amdt 5 (baby-loss certificates after termination) signed FOR; blasphemy repeal deliberately unsigned; four struck; former MLAs listed from the vote record
metadata:
  type: project
---

**Decided by Christopher, 6 Sept 2026** (`config/nia_votes.yaml`), after the
amendment texts and archived Hansard were read:

- **Signed, our side FOR:** Justice Bill Amdt 97 (30 Jun 2026, fell 32–48) — no
  man in prison accommodation where women are held, sex per Equality Act
  s.212(1). Deaths, Still-Births and Baby Loss Bill Amdt 5 (4 Nov 2025, fell
  23–53) — baby-loss certificates on request after a termination. Sentences
  describe the act, never motive. mla-votes.html now carries verdicts.
- **Deliberately UNSIGNED:** Justice Bill Amdt 73 (9 Jun 2026, passed 57–24),
  abolishing common-law blasphemy. Free-speech reading (consistent with our
  line against blasphemy laws abroad) vs the DUP/TUV position; UUP voted for.
  Do not propose a side again unless asked.
- **Struck (`not_ours`):** the waste-and-inefficiency motion (tagged via one
  word) and the three Executive's-Approach-to-Hate items — no vote rows, and
  the 22 Sept 2025 Hansard is not archived, so whether the Assembly divided
  cannot be shown; as tracked divisions they'd render "no vote recorded" for
  all 90 MLAs.

**Mechanics:** `tools/ni_classify.py` is the ONLY writer of `ni_divisions.areas`
(the collector inserts null) and re-derives weekly, so `not_ours` is honoured
there. The NI roster (`ni_members`) is current-only with no end dates, so
voters absent from it (William Irwin, Gary Middleton — DUP, departed) are
listed by `make_devolved_votes.py` from `ni_votes.member`/`designation`,
labelled former, and counted in the build output.

**Sidecar conflicts resolve themselves since 7 Sept 2026:** `tools/merge_sidecar.py` (bound by `.gitattributes`, installed into local git config by `db_state.py --pull`) takes whichever side names the release asset's sha256 digest (`gh api … .assets[].digest`); with no digest it takes the later `published_utc`; with neither it stops and says so. See [[parl-monitor-store-guard]].

Related: [[parl-monitor-welsh-verdicts]], [[parl-monitor-everyone-who-voted]].
