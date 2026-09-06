---
name: briefing-outcome-persecution-verbs
description: OUTCOME lacked martyred/destroys/criminalises; and ABOVE is for said-vs-happened, never subject matter
metadata:
  type: project
---

`OUTCOME` — the regex deciding the said-versus-happened axis — was missing **25 verbs**, all of
them the persecution beat's own vocabulary: *martyred, beheaded, executed, massacred, lynched,
demolished, razed, torched, bulldozed, desecrated, seized, confiscated, outlawed, criminalised*.
It had *killed/murdered/abducted/jailed* but not the words those stories actually use, so on
31.08.2026 "Baptist Pastor Martyred in Myanmar" and "Chinese Gov't Destroys Church Worth
Millions" both scored **i2** — zero outcome credit, because the verb carrying the whole event was
unmatched. Fixed with **verb forms only**.

Separately, an animal being put down classified as `('Life', 6)` — same section and weight as a
genuine assisted-dying story. `is_animal_euthanasia()` now vetoes it in `classify()` before any
keyword scoring. 49 hits across 16,146 archived candidates, all genuinely animal stories; the one
imperfect case ("Official kidnapped, tortured for culling dogs in Pakistan") loses its section
rather than reaching Politics, left as-is rather than over-engineered.

**Two lessons worth more than the fix.**

**ABOVE pairs are for said-versus-happened, scale and commentary — never subject matter.** Three
pairs were written comparing a martyred pastor against a court order about two dogs, on the
reasoning that a human obviously outranks an animal. Once the verbs were added both sides scored
i8 and nothing would separate them: `importance()` does not model subject matter, it is a reading
order heuristic. Keeping them meant a permanently red fixture or a subject-matter hack bolted
onto the scorer. The animal problem was real — it was a CLASSIFIER defect, and that is where it
belonged. When an ABOVE pair will not go green, ask whether it is even the right instrument.

**A flat concordance can be the CORRECT result, not a null one.** 0.642 → 0.642, top-40 0.43 →
0.42. This change promotes persecution stories the curator FAILED to pick, so their archive label
is 0 — a right fix must read flat-to-negative, and a gain would have been suspicious. See
rank_eval.py's header on concordance measuring revealed preference, not correctness. Guards did
the real work: bare `criminalis` matched "deCRIMINALISes", and the nouns `destruction` and
`demolition` gave outcome credit to a lament and to a council *seeking* permission.

Also found: **`rank_eval_log.txt` had never been backed up** by any list in state_sync.sh, and
`test_all_scripts_backed_up` could not see it because that test only walks `.py` and `.sh`. Now in
JUDGEMENT_FILES (43 files). Related: [[briefing-relay-not-primary]],
[[briefing-markup-becomes-testcase]], [[briefing-rank-eval-corpus]].

**The backup invariant covered scripts only — widened 31.08.2026.** `test_all_scripts_backed_up`
walked `*.py` and `*.sh`, so an unbacked `.txt` raised nothing. `test_all_data_files_backed_up`
now parses STATE_FILES **and** JUDGEMENT_FILES and walks `*.txt`/`*.json`/`*.opml`, reporting
three states rather than two: **MISSING** (fails), **DERIVED** (named with the command that
rewrites it — an unexplained absence must never be *inferred* to be this), **ORPHAN** (in no
list, read by no code; noted, not failed).

It found a second instance of the bug it was written to prevent, within a minute:
`repeat_eval_log.txt`, which `shortlist.py:1764` cites by name. Verified by **mutation** — pull
`tiers.json` out of the list and the test must fail — because a green run proves nothing about
whether an assertion is wired to the real path (the `cluster_rank` lesson in
[[briefing-relay-not-primary]]).

It also surfaced `briefing-sources.opml`, an orphan beside the live `sources.opml`. Before
deleting an orphan config file, diff it against the live one: this had 164 feeds absent from
`sources.opml`, and only checking `extra_feeds.txt` (which supersedes the OPML) showed all 164
domains were already covered. "Nothing reads it" is not sufficient grounds on its own.
state_sync.sh: 42 files -> 44.

**DERIVED moved to the writer, 31.08.2026 — and why it stayed a declaration.** The derived-file
list was in `run_tests.py`, where anyone hitting a red run could append to it and reproduce the
gap. It now lives in `compose.py` as a module-level `DERIVED_OUTPUTS` tuple beside the two
`open(..., "w")` calls, and the test parses it out of every `*.py` with **ast** — a declaration
is reliably parseable where a usage pattern is not. A file declared derived *and* present in a
backup list now fails as a contradiction.

**Inference was attempted and abandoned, for a reason worth keeping.** Scanning for
`open(NAME, "w")` found no access at all for 8 of 19 data files (they are written through
helpers). More decisively, the only property a static pass can see — "written but never read
back" — is **false** for both derived files: `mark_published.py` reads `expected_urls.txt` and
`composed.json`, `archive_day.py` reads `composed.json`. What makes them derived is that one
command recreates them whole from backed-up inputs, which no static analysis establishes. Truly
deriving it would mean deleting each candidate and confirming the pipeline rebuilds it — a full
run, so it does not belong in a fast offline fixture.

Mutation-tested four ways (declaration emptied; a backed-up file wrongly declared derived; a
judgement file dropped from state_sync; a new undeclared data file on disk) — all four fail,
baseline restores to 386/0.

**The full rebuild check was costed and rejected, 31.08.2026 — do not re-propose it lightly.**
"Delete each derived file and confirm the pipeline rebuilds it" sounds like the rigorous version.
It is not, for one decisive reason: **delete-then-rebuild disarms two guards in order to run.**
Without `composed.json`, `mark_published.py` stops refusing a stale run and marks every pick
"including any a section cap dropped" — burning cap losers that must stay available. Without
`expected_urls.txt`, the only check that catches an *invented* URL is gone. A network flake
mid-rebuild leaves both down in a directory whose next command may be `mark_published.py`. **A
test must not be able to cause the fault it checks for.** Cost is also prohibitive: rebuilding
needs `/tmp/today.json` *and* `/tmp/picks.json` (both ephemeral), plus network; ~4-5 min against
the fixture's ~2s offline. If it is ever built: separate script, deliberate invocation,
throwaway COPY of the directory, files moved aside rather than deleted.

What went in instead: each declared derived file must have a **writer**, detected by inspecting
the ~40 chars after the filename literal. Took four attempts — `[^)]*` breaks on the `)` inside
`os.path.join(HERE_DIR, "composed.json")` — and that brittleness is itself why the declaration
lives beside the writer and the test only sanity-checks it. Mutation-tested three ways (declare a
file nothing writes; rename the writer leaving the declaration; declare a judgement file derived
*and* drop it from backups) — all fail, baseline 386/0.

**Also: a shared failure list needs a message that fits every class in it.** The first version
hard-coded one class into the prefix and printed "not declared derived: X is declared derived by
compose.py" — a contradiction, in the message someone reads at 6am when the morning run stops.
