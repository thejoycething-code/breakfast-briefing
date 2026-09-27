---
name: intel-reports-verified-from-store
description: The quarterly England political intel reports are verified against the parl-monitor store; what the store can and cannot close
metadata:
  type: project
---

The Cluster 3 England reports in Drive are a companion pair: "England - Living
Political Intel Report Q<n>" (quarterly, doc 1YQ7PgWteGd4fWcVHF3RIQXUDDNvMnjeMlKSPyON2pxo)
and "England - Political System Map" (structural baseline, doc
1guS8RczdEHOJKT222-VkDX6AwdwwTweivrSoSSVUhj0). The quarterly carries an explicit
"Open items to verify (⚑)" list, which is the hook: run each ⚑ against
`~/parl-monitor/data/parl-monitor.db` and the dated CSVs in `data/5ca/`.

**Why:** the reports were being written from web research while the monitor
already held the answer. On 21 Sept 2026 the store closed the report's own top
Q4 task (rebuild the 5CA from the Division 2428 roll) which the tool had already
done that morning, and contradicted a dated claim about a Stormont Second Stage.

**How to apply:** the store closes anything that is a UK Parliament or devolved
division, roll, bill stage, member seat, petition, consultation deadline or
committee publication. It cannot reach Tynwald, legislation.gov.uk commencement
SIs older than the rolling window, court listings, regulator guidance or party
conferences; say so rather than leaving those silently open. `items` is a
rolling current-window table, not an archive, so absence there is not evidence.
Party 5CA aggregation from the 5CA CSVs must split `Decision-Maker` on the first
comma inside the trailing parens and fold `Labour (Co-op)` into Labour, or the
seat counts will not reconcile to 649. See [[parl-monitor-5ca-election-mockups]]
and [[uk-campaign-calendar]].

**Section 1's table is whole-agenda; section 2's are per topic (set 21 Sept 2026).**
The quarterly's section 1 party 5CA must answer "who is a champion generally",
so it is an MP-level aggregate over the topic sheets, never one topic dropped
into that slot. Christopher's rule: **++ = never - or -- on any topic and ++ on
at least one life issue; + = never -- on life; -- = -- on two or more life
issues; 0 = no directional evidence.** On the 21 Sept sheets that gives 59
champions in the House (Conservative 48, DUP 5, Reform 2, TUV 1, UUP 1,
Independent 2) and **Labour 0 ++ / 32 +**.

**Why:** 377 of 649 MPs are with us on some topics and against on others, so a
single number per party flatters or libels nearly everyone. Putting the
assisted-dying table in section 1 made "145 Labour ++" read as 145 Labour
champions when Labour is 20 ++ / 357 -- on abortion.

**How to apply:** the aggregate spans life, family and freedom and nothing else
— LIFE: abortion, assisted-dying, surrogacy-embryology; FAMILY: marriage-family,
parental-rights-education, conversion-practices, gender-medicine-children,
sex-based-rights; FREEDOM: free-speech-privacy-and-civil-liberties,
freedom-of-religion. `prostitution-trafficking-and-sexual-exploitation` is the
only sheet outside the three and is excluded on that ground, not case by case.
Corroborating: it places John Hayes and Danny Kruger at --, and counting it cuts
the Conservative ++ row from 48 to 25.
Use the absence-corrected assisted-dying column (see
[[parl-monitor-vote-feeds-5ca]]). The Speaker has no party row, so party rows
sum to 648 against a total of 649; say so in the Total cell or someone will
re-add the columns and query it.
