---
name: parl-monitor-de-keyless
description: The keyless German sources — PDF protocol fallback (de_btp, needs de-hyphenation) and the MdB-Stammdaten register (4,614 members since 1949, religion deliberately not stored)
metadata:
  type: project
---

Built 26 September 2026. Only DIP needs a key; abgeordnetenwatch, dserver,
the Tagesordnung, the Mediathek and e-petitions are keyless already.

**PDF protocol fallback** — `src/de_btp.py`, `de_speeches.py --source pdf`.
Listing answers plain curl (4,656 protocols); documents at
`dserver.bundestag.de/btp/<wp>/<wp><nnn>.pdf`, sitting number padded to
THREE digits (21/96 → 21096.pdf). No XML on that route despite a published
DTD — `.xml` is a 404.

**How to apply:**

- **Measure equivalence by normalising first.** On 21/96: 474 speeches from
  each source, 136 of 137 speakers shared, 464/474 bodies verbatim. Raw
  prefix comparison said 33/474 — an artefact of line breaking that nearly
  binned the route.
- **De-hyphenate or the term list under-matches silently.** 3,467
  hyphen-newline splits in 21/96, none in DIP's text. 11 on-our-ground
  speeches became 13 (DIP: 14) after `dehyphenate()`. Rejoin only when the
  next line is LOWER CASE — a capital means a real compound.
- `--source pdf` asks for **no DIP key**: a fallback needing the thing it
  survives is not a fallback.
- Cost: 1.7 MB and ~4s a sitting. Fallback, never the default.

**MdB-Stammdaten** — `tools/de_stammdaten.py` → `de_mdb`, `de_mdb_terms`.
4,614 members, 13,046 terms, WP 1–21, keyless, loaded ON DEMAND (registered
in coverage as such; re-run after a general election).

- **532 members carry an ORTSZUSATZ**, and 26 surnames are held by more than
  one sitting WP21 member (Schmidt ×8, Müller ×6). That is why the Bericht
  writes "Michael Brand (Fulda)" — see [[parl-monitor-de-debate-packs]].
- **Current name = the one with no HISTORIE_BIS.** 434 names across 400
  members; taking the first gives decades-old names.
- ORTSZUSATZ arrives as `(Fulda)`; brackets stripped on store.
- **RELIGION is in the file and is NOT stored** — special category data, not
  necessary here. Named in db.py, the tool and a test so it reads as a
  decision.
- Different id space from `de_members` (abgeordnetenwatch): join by name.

Related: [[parl-monitor-germany]], [[parl-monitor-de-debate-packs]].
