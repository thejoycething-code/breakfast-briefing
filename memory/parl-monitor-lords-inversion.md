---
name: parl-monitor-lords-inversion
description: All three Lords divisions shipped with inverted verdicts; a division's QUESTION comes from motion notes, never its title
metadata:
  type: project
---

On 31 Aug 2026 Christopher caught Lord Alton's page carrying BAD votes on
assisted dying. All three Lords divisions (981, 1885, 1886) were inverted:
their titles are just the bill name, and they had been read as votes ON the
bills when each was actually an amendment moved by the Bill's OPPONENTS —
981 was Carlile's six-month delay that STOPPED Joffe's Bill 148–100; 1885
was O'Neill's plain-language amendment (Contents included Alton and Carlile,
Not-Contents included Falconer, the sponsor); 1886 Carlile's two-doctors
safeguard. Falconer's 2015 Bill had an UNOPPOSED Second Reading — no
division on the principle exists. Inverted verdicts were live from 29 Aug to
31 Aug. Same commit fixed the hardcoded /Commons/ record link on Lords rows.

**Why:** sign-off checked the wording against a mistaken reading of what the
division WAS; nobody read the motion text.

**How to apply:** before scoring any division, read the Lords Votes API's
`amendmentMotionNotes` (or the Commons equivalent question text) and check a
known partisan's side against the rolls (Alton = anti-assisted-dying) — a
title alone never identifies the question. Verdicts corrected to
our_side: aye on all three; Christopher reviewed the evidence and signed the
corrected wording off the same day (31 Aug 2026), so they are live.

The method then audited the other 18 (Commons) divisions the same day: all
clean. Kruger sat exactly on our_side in all 16 he voted in, and the one he
missed (1580, the ten-minute rule bill) was anchored by its own mover —
Bridgen in the Ayes, Shannon and Hollobone telling. Why the Commons entries
were safe: their titles NAME the clause or motion ("Report Stage: New
Clause 1"), while a Lords division's title is just the bill name — so the
Lords is where this failure mode lives, and any future Lords division gets
the motion-notes + partisan-anchor check before a meaning line is drafted.
Useful anchors: Alton (anti-assisted-suicide, Lords), Kruger (Commons),
Falconer (pro-assisted-dying, Lords). See [[parl-monitor-build]].
