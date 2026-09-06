---
name: parl-monitor-senedd-waf
description: business.senedd.wales is WAF-blocked; which Welsh hosts still answer and what was re-sourced onto them
metadata:
  type: reference
---

**business.senedd.wales has been behind an Azure WAF since about 2026-08-25**
(last good run 24 August). It returns **403 to every non-browser client**:
the honest UA, the authorised browser UA, and full browser
Accept/Sec-Fetch headers alike, from this laptop and from GitHub's runners,
on the host ROOT as well as any page. Do not waste time on header tricks --
that was checked exhaustively. It looks like a JS challenge.

**The WAF spread to `senedd.wales` for DATACENTRE IPs on/before 5 Sept 2026.**
The committee index answers a laptop and returns 403 to GitHub's runners, so
`tools/sd_committees.py` failed the Senedd weekly every run. It now treats an
unreachable committee list as a GAP (recorded, printed, exit 0) rather than a
crash — safe only because `sd_committees` is a cadence-checked feed in
`tools/coverage.py`, which DMs if the data really stops refreshing. Test the
HOST FROM CI, not from this laptop: they now get different answers.

**Hosts that still answer (from a laptop, honest UA):**

* `senedd.wales` -- committee index, each committee's own page (carrying the
  ModernGov CommitteeId AND the "will next meet on ..." prose), and the bill
  register table with IId, title, stage column and progress sentence.
  **403 from GitHub runners since ~5 Sept 2026.**
* `record.senedd.wales` -- the Record of Proceedings. Committee transcripts
  via `/Search/SeeMore` (**answers JSON containing ESCAPED html fragments**,
  so a regex over the raw response finds nothing) and `/Meeting/{id}` pages
  with agenda items, contributions, speaker names and ModernGov UIDs.
* `www.gov.wales` -- browser UA only, as before.

**Re-sourced 2026-08-28** onto those hosts: `tools/sd_committees.py` and
`tools/sd_bills.py`. Both are better than what they replace -- the Record is
the transcript itself, and the bill register was FRESHER than the store.

**The one thing that could not be verified.** `mgWhatsNew` was how a
brand-new bill was caught the week it started moving, and it is gone.
Discovery is now the register, which is headed "Progress of Senedd Bills"
and should list a bill from introduction -- but every row reads "Act" today
(the Seventh Senedd has introduced none) and the archive page no longer
renders its table. **When the first live bill of this Senedd appears, check
it shows up with an in-progress stage** rather than only on Royal Assent.

Related: [[parl-monitor-store-divergence]], [[parl-monitor-build]].
