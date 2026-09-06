---
name: meta-silent-failure-pattern
description: "The Meta Reports project's characteristic bug is something reporting success while achieving nothing — five instances, and the guard each one now has"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2168d5ed-2f28-4dd8-af26-046baad76925
  modified: 2026-08-29T18:56:01.625Z
---

Every serious bug in [[meta-organic-reports]] has had the same shape: a step
reported success while achieving nothing, and each was found by accident rather
than by a test.

1. **PostgREST caps responses at 1,000 rows** (Supabase `db-max-rows`) and
   **ignores a larger `limit` in the query string**. `loadAll` asked for 100,000,
   got exactly 1,000, returned it as complete. Every aggregate was computed on 44%
   of the data. Worse, posts and metrics truncated *independently*, so posts whose
   metrics fell outside the first 1,000 appeared to have no metrics — manufacturing
   a "343 posts with no metrics" figure when the truth was 68, which led to a wrong
   diagnosis being reported to the user (a token scope problem that did not exist).
2. **A redactor corrupted the very tokens it protected** — redacting at fetch time
   meant the collector read `"<redacted>"` as a token.
3. **An assertion ending `|| true`** — unfailable, and passing.
4. **A heartbeat committed and pushed nothing while reporting success** —
   `actions/checkout` leaves detached HEAD, so a bare `git push` had no refspec.
5. **`outliers` returned 439,241 characters** by listing every post outside
   0.5x–1.5x of the median. Fine at 400 posts, unusable at 2,700, with no code
   change in between.

**Why:** plausible output is not evidence of correct output. In every case the
answer looked reasonable — just wrong, or partial, or empty in a way nothing
surfaced.

**How to apply:** for anything that reports its own success, ask what it would
look like if it had silently done nothing, and assert against *that*. Concretely
in this repo: `scripts/test-truncation.js` (mock reproduces `db-max-rows` with
`--cap`), `scripts/test-tool-size.js` (seeds 600 posts, caps every response), and
the watchdog's completeness check (compares what tools receive against an
independent `count=exact`, which needs no rows and so cannot itself be truncated).

**Never silently truncate.** When a cap is applied, state what was left out —
`"Showing the 25 most extreme of 1,172"`. A silent cap reads as "this is all of
them", which is how a partial answer gets quoted as a complete one. Same principle
as the briefing project's rule against silent suppression
([[briefing-silent-suppression]]).
