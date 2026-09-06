---
name: parl-monitor-welsh-verdicts
description: Welsh LCM decisions of 6 Sept 2026 — CWS Bill LCM signed AGAINST, Crime & Policing LCM struck as not_ours; the not_ours mechanism and why abortion is reserved in Wales
metadata:
  type: project
---

**Decided by Christopher, 6 Sept 2026, after both Records were read.**

- **Children's Wellbeing and Schools Bill LCM (17 Mar 2026, agreed 37–13): SIGNED, our side AGAINST.**
  The consent extended the children-not-in-school register and council
  permission to deregister to Wales (Cefin Campbell for, Asghar/Isherwood
  against on mandatory registration of home educators). Card sentences
  describe what the vote DID, never motive — several Conservative speeches led
  on competence as well as substance. First Welsh verdict on ms-votes.html:
  13 good, 37 bad, 10 unrecorded.
- **Crime and Policing Bill LCM (10 Mar 2026, refused 25–27): STRUCK (`not_ours`).**
  Title-tagged abortion via s.241, but **abortion is a reserved matter in
  Wales** — GoWA 2006 Sch 7A, Head J, Section J1 — so the consent could not
  cover it; refusal reasons were AI/facial recognition/non-crime hate incidents
  (Con), concurrent powers (Plaid), "doesn't go far enough" (Reform). Nobody
  said abortion.

**`not_ours` is honoured in THREE places** because `sd_divisions.py` re-derives
areas from the title every weekly run and a store-only fix returns on Thursday:
the collector writes `[]`, `make_devolved_votes.py` never lists it,
`devolved_score.py` never scores it. Pattern is reusable for Holyrood/NI.

**Lesson paid for the same day:** I anchored a patch on `from src import db`
when the real line was `from src import db, filter as filt`, shipped a
SyntaxError to main, and the rest of the batch aborted silently. Parse before
writing; gate commits on the suite; never `git add -A` after a heredoc that
may have failed.

Related: [[parl-monitor-lords-inversion]], [[parl-monitor-5ca-surfaces]].
