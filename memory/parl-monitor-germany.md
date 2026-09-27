---
name: parl-monitor-germany
description: Bundestag monitor scoped and phase 1 built 22 Sept 2026 -- the English taxonomy is blind to German, which gates everything else
metadata:
  type: project
---

Scoped in `docs/germany-scope.md` (probed live, 22 Sept 2026) and phase 1
built: `tools/de_rollcalls.py` into `de_members` / `de_divisions` / `de_votes`.

**The blocker is language, not data.** `config/taxonomy.yaml` is English and
matched 5 of the current Bundestag's 68 recorded votes; four matched only
because "Migration" is spelled the same, one of those being the Chancellor's
budget. So `de_divisions` deliberately has NO areas, tier or triage columns,
and stores every recorded vote plus the API's own German topic labels. Do not
add classification until the German term layer exists, and draft it with
somebody who reads German politics: German compounds break substring matching
(`Schwangerschaftsabbruch` contains `Schwangerschaft`; `Lebensschutz` and
`Lebensmittel` share a stem).

**Sources.** abgeordnetenwatch.de/api/v2 is open, no key, covers the Bundestag
(parliament 5, legislature 161 = 2025-2029) and all 16 Länder; one call per
poll returns every member's position with their Fraktion.
dserver.bundestag.de serves Drucksachen as PDF, so `src/eudoc.py`-style body
matching will work. **DIP (search.dip.bundestag.de) is 401 without a key the
Bundestag issues on application** -- that is the only blocking dependency and
it gates the volume phase.

**Why votes alone are not a monitor.** 230 recorded votes across two
legislatures contain five items on our ground (1 abortion, 2 assisted dying,
1 self-ID, 1 free speech). The Bundestag reserves recorded votes for
set-pieces; our issues move through motions and plenary debate, in DIP.

Open for Christopher: who requests the DIP key; who drafts the German terms;
Länder in scope or not; own edition or a section (the devolved precedent was
sections). Related: [[parl-monitor-eu-monitor]], [[taxonomy-v16-areas]].
