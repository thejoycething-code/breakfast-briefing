---
name: parl-monitor-de-debate-packs
description: German debate packs — the Mediathek (one video per speech, wall-clock) decides who spoke, not the Vorabfassung protocol; align speeches by ORDER, never surname alone
metadata:
  type: project
---

`tools/de_debate_pack.py` + `src/de_debatepack.py`, built 25 September 2026
once the bundestag.de block lifted. Same four files as Westminster
([[parl-monitor-debate-pack]]): roundup, checklist, quotes, shotlist.

**How to apply:**

- **The protocol has NO per-speech timecodes.** 21/96: four "Uhr" mentions
  in 858,106 chars, three about voting urns. Do not interpolate from
  `Beginn:` — that sitting ran to 02:15.
- **The Mediathek publishes ONE VIDEO PER SPEECH** with speaker, party and
  wall-clock start. Endpoint (plain curl, no browser):
  `bundestag.de/ajax/filterlist/de/mediathek/442338-442338?limit=8&offset=N&sitzung=442332%23<nr>&wahlperiode=442334%23<wp>`.
  8 rows a page whatever `limit` says; total is `data-hits` (309 for
  sitting 96, ~39 requests). `Gesamter TOP` marks the whole-debate entry —
  its person block holds a photo caption, not a name.
- **The speaker list comes from the RECORDING, not the text.** DIP serves a
  *Vorabfassung* on the day: sitting 96 ran TOP 7, 8, 9, 10, **12** — item
  11 was absent while the Mediathek had it on video. Report how many
  speakers the protocol covers, so omissions can't read as silence.
- **Align by ORDER, never surname alone.** The protocol is the whole sitting
  day, so the first "Brand" may be five hours away. `align_bodies` takes the
  contiguous run matching the recording's order.
- **Topic terms must be STEMS.** German compounds: heading says
  "Transplantationsgesetzes", speeches say "Transplantation". Verbatim
  matching returned nothing in a debate entirely about it.
- **Drop the presiding officer** — they appear in the Mediathek like anyone
  else (Ortleb had 3 entries in one debate, all procedural).
- **Footage is LINKED, never downloaded.** Bundestag terms unread; that is a
  human decision. (Westminster downloads under PRU terms.)

**Collector recall bug found here, fixed in `src/de_protocol.py`** (the
parser moved there so packs and collector share one copy): `Michael Brand
(Fulda) (CDU/CSU):` and `Karl-Josef Laumann, Minister (Nordrhein-\nWestfalen):`
never matched — 5 headings in 21/96. **Protocols read before 25 Sept were
parsed without the fix; those speeches are still missing from the store.**

Related: [[parl-monitor-debate-pack]], [[parl-monitor-germany]].
