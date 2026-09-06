---
name: briefing-gnews-decode-truncation
description: Google escapes "=" as \uXXXX in the garturl payload; the decoder cut every URL at its first query value
metadata:
  type: project
---

The batchexecute decoder truncated **every** URL carrying a query string, for as long as it
existed. Google escapes characters inside the garturlres payload as `\uXXXX`, double-
backslashed because the JSON string is nested in another, and `=` is the one that matters —
every query value begins with one. `_GARTURL_RE` captured `[^\\"]+`, which stops at the
backslash, so `...obituary?id=62306633` came back as `...obituary?id`. Fixed 31.08.2026: the
run allows escape sequences and `_unescape_garturl` decodes them.

**Why it stayed invisible for so long:** it never published a wrong link. `_looks_truncated`
plus the title check caught the wreckage and fell back to keeping the redirect, so the entire
cost was booked as "could not be resolved" — a number the brief treats as a health metric and
tolerates at single digits. Every one of those was a story the ranker then read on its headline
alone. It surfaced only because two affected items were porn spam injected into a compromised
Smithsonian host and reached a live section (see [[briefing-porn-spam-gate]]).

**The trap in fixing it, and the real lesson.** Repairing the truncation alone would have made
things *worse*. `resolve_one` treats a well-formed decode as authoritative and returns it
without a title check — deliberately, because verifying would discard correct decodes from
publishers that block the fetch. But Google returns a paginated **category index** for some
feeds: nine Premier Christian News stories all decoded to `/category/uk-news?page=<n>`. While
truncated they failed the structural gate and were dropped; once clean they would have
published as nine article links to one listing page. So `_looks_like_index` now routes
index-shaped decodes through the same confirm-or-drop path. It is syntactic on purpose — a
numeric `page=` param or an index path segment — so a genuine article URL from a blocking
publisher is never thrown away.

**How to apply:** when a gate stops firing because an upstream bug was fixed, check what that
gate was silently catching. Measured on the 31.08 sweep: 9 of 21 redirects now resolve to real
articles, 12 correctly keep the redirect. Both behaviours are covered offline in run_tests.py
(`test_gnews_decode_unescape`, `test_gnews_index_decode_flagged`) with payloads captured off
the wire. Related: [[briefing-decode-gnews-links]].
