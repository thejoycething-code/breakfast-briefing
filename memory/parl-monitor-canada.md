---
name: parl-monitor-canada
description: "Canada scoped 26 Sept 2026 — English taxonomy works (unlike Germany); phase 1 House divisions/bills built dormant; misses were Canadian NAMING (Digital Safety Act, \"pregnant\", \"pornographic\")"
metadata:
  node_type: memory
  type: project
  originSessionId: 3741c313-0a64-49f5-b304-d7ff4155e755
  modified: 2026-09-26T12:34:30.329Z
---

Scope in `~/parl-monitor/docs/canada-scope.md`. Phase 1 is `tools/ca_rollcalls.py`,
which writes `ca_members`, `ca_divisions`, `ca_votes` and `ca_bills`, with 13 tests.
The schema lives in `src/ca_store.py` (fold it into db.init_db on adoption) and
the additions in `config/watchlist-ca.yaml`. Nothing is scheduled. The live run
went into a scratch db only, never the store.

**Key finding:** the English taxonomy works for federal Canada, which is
bilingual. It found 12 of 174 divisions (45-1) and 12 of 928 (44-1) on our
ground, excluding migration. The misses were names, not language:
- C-34 "Digital Safety Act", where the taxonomy knows the UK "Online Safety Act"
- C-311 "violence against pregnant women"
- C-270 "pornographic" against the term "pornography"
- C-9 matched area 7 only; the religious-text defence it removes is area 8

**Sources:** ourcommons XML (divisions per session, per-division member
positions with caucus-at-vote, Hansard per sitting with 5-min timestamps) and
LEGISinfo JSON are open and keyless. Petitions come by POST to
`/petitions/en/Petition/SearchAsync` only; `?output=xml` gives HTML. The Senate
is HTML only (36 votes in 45-1). Bill text is PDF only. Gazette RSS returned 503
on 26 Sept.

**Commit accident, 26 Sept:** the German session's commit dfdb7b09 (pushed)
swept in `src/ca_store.py` and the first watchlist-ca.yaml draft. The rest of
the Canada files were left uncommitted.

**How to apply:** open questions for Christopher are in the doc: reader/edition,
provinces (Quebec needs a French layer), watchlist review, and stemming
"pornograph*" repo-wide. Tally gap: 44-1 division 609 has 132 Nay rows against
a tally of 133. Related: [[parl-monitor-germany]], [[parl-monitor-store-guard]].

**Phase 2 (26 Sept):** `tools/ca_hansard.py` and `tools/ca_petitions.py`, 19
tests in `tests/test_ca_hansard_petitions.py`, and four more tables in
ca_store.

- Hansard `DbId` is a member IN A ROLE, never a PersonId. It is resolved by
  riding, then by unique name, then remembered in `ca_speaker_roles`.
- **Petitions: never use SearchAsync or the XML export.** Both sit behind a
  reCAPTCHA token. Walk the public Details pages instead: the contiguous
  451-NNNNN presented numbers (an e-petition gets a 451 number when
  presented), plus a sparse e- probe floored at E_SEED 7810.
- "medical assistance in dying" is TIER 2 in the shared taxonomy. Passages
  need tier 1 or a watchlist hit, so it went into watchlist-ca. That fix took
  sittings 138-144 from 30 to 35 speeches.
- Backfills are about 40 MB of Hansard and 140 MB of petitions for 45-1; run
  them from CI, and announce them.

**Phase 2b (26 Sept):** `tools/ca_senate.py` and `tools/ca_gazette.py`, 16
tests in `tests/test_ca_senate_gazette.py`.

- **The Senate is HTML only.** A details page lists EVERY seated senator, and
  unmarked rows are stored as "Did not vote". The list's tally is the parse
  check: a mismatch is a gap.
- **Gazette RSS lists issues, not items.** A notice is an anchor on a shared
  page, so the page is fetched once and cut at the anchors, and its text is
  stored. CRA charity revocations name the charities only in the text.
- An extra edition's link IS the document, not an index.
- An issue with a failed item is never marked read.
- Over 60 days there were 3 matches, all noise (Ebola orders on IHR, an
  immigration regulation).

**Phase 3 (26 Sept):** the Canadian 5CA. `tools/ca_5ca.py` reads
`config/ca_stance.yaml`, has 16 tests, and writes stable filenames
`data/5ca/ca-5ca-<chamber>-<area>.csv`.

- **All 30 stance entries are Claude drafts, so nothing places.**
  `test_the_real_stance_file_loads_and_nothing_in_it_is_confirmed_yet` fails
  the day a flag goes; check a HUMAN removed it.
- **The absence cap uses the latest division where OUR side scores +2.** The
  abs() version capped C-314 voters for missing the C-62 delay.
- **The lobby check applies only then**, and totals count sitting members only.
- **C-9 is verified from the bill PDFs.** The s.319(3)(b) repeal was added at
  committee, and the Senate's only surviving change was "a noose".
- **The Canadian tables were undeclared from phase 1**, failing test_db inside
  Deploy tracker. They are now in `db.TABLES`, `init_db` calls
  `ca_store.ensure_schema`, and `coverage.EXEMPT` names the dormant ones.
- **Run the FULL suite before committing** here, not just the ca_ tests.

**Seven texts pulled (26 Sept).**

- **Where the texts live.** A House division page
  (`ourcommons.ca/members/en/votes/P/S/N`) carries the motion text, the mover
  and the sitting. Senate texts are in the Journals, linked from the vote
  table.
- **Texts overturned the guesses:**
  - Martin does NOT restore s.319(3)(b); it rewrites the 11.1 safe harbour.
  - The Senate made one amendment (the noose).
  - The RIDR report created a residential-school "denialism" offence.
  - House 92 (Brock) is the clause-specific restore-319(3)(b) vote.
- **All 22 readings are still drafts.**
- **Bug fixed:** a confirmed entry with one side blank used to crash.

**Scheduled (26 Sept, pushed 63ebd336; first hand run 36271294106 green, sidecar 741e7db1):** `.github/workflows/ca-weekly.yml`
runs Tue 10:00 UTC with a 12:00 gated retry.

- An empty store starts at SEED_SITTING 138 and PRESENTED_SEED 1190.
- The backfill runs only on hand dispatch with backfill=true, and reads what
  is MISSING below the highest held.
- coverage.py: FEEDS ca_divisions/bills/members/petitions; ONCE_EVER
  ca_senators/sittings/gazette_issues. read_at is a business date, never a
  FEED column.
- The raw_state pull and push are required in every store publisher.
- On 26 Sept the German session had uncommitted taxonomy edits failing
  test_taxonomy_sync; they were not Canadian.
