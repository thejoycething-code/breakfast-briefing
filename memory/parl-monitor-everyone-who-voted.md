---
name: parl-monitor-everyone-who-voted
description: Every tracker lists anyone who cast a tracked vote, labelled former if they have left; seats belong to whoever holds them now
metadata:
  type: project
---

Christopher, 4 Sept 2026: "Make sure all politicians are included, whether
it be the Senedd, Holyrood or elsewhere." Every tracker listed only SITTING
members, hiding 32 Welsh Members of the Sixth Senedd (Mark Drakeford, the
First Minister), 65 MSPs and 344 MPs — on exactly the divisions the pages
exist to report.

**The rule, now the same in all four chambers:** a member is listed if they
sit OR if they cast a vote we track; a member who has left is LABELLED
former. A member who has left with nothing to show stays off.

**Why:** the tracked divisions are often from the previous term (Welsh LCMs
March 2026, Scotland's assisted dying Bill March 2026, both chambers
re-elected in May), so a sitting-only list hides the very people who decided
them.

**How to apply:**
- A SEAT belongs to whoever holds it now. Former members are excluded from
  the constituency index and seat searches, or a postcode lookup answers
  with the MP who lost that seat.
- A former member's SILENCE is not an absence. Parliament publishes no end
  dates for the 344 former MPs and `servedOn()` fails open, so every
  division after they left would read "DID NOT VOTE" — the same falsehood
  the page once told peers. They get "FORMER MEMBER" and a card saying we
  cannot date their departure. **Open gap:** no service end dates exist for
  them; pulling those from the Members API would let the page say "had left
  by then" properly.
- A recorded vote always beats membership dates: 29 sitting Welsh Members
  voted in the previous Senedd under the same id.

Related: [[parl-monitor-devolved-identity]], [[parl-monitor-lords-inversion]].
