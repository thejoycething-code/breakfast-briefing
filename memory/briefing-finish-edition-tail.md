---
name: briefing-finish-edition-tail
description: "Run ./finish_edition.sh for the briefing tail rather than hand-running steps 5-9; --allow-reclass is unconditional there by Chris's decision"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34a4a19a-f466-4c64-8c5c-faf543c1d7bd
  modified: 2026-08-26T06:32:18.386Z
---

Run `./finish_edition.sh` for steps 5-9 of the Breakfast Briefing. Do not hand-run the tail
unless the script genuinely fails. Chris, 26.08.2026, after that morning's edition skipped it:
"run finish_edition.sh for real tomorrow".

Its compose call passes `--allow-reclass` **unconditionally** — Chris, same day: "make it
unconditional, I always check the numbers anyway." So the classifier-mismatch list is a report,
not a gate. It still prints to stderr just above `composed N items`; read it, and say in the
final message that reclassed picks were deliberate.

**Why:** on 26.08.2026 the script was skipped because its compose call lacked the flag and
`set -e` turned compose's refusal into a stop — 31 picks were deliberately off-classifier, 27
of them rescued from the two SUPPRESSED blocks, which reach no section at all and so are
"mismatches" by construction. Steps 5-9 were run by hand instead. A second latent abort was
found the same session: `set -u` plus this Mac's **bash 3.2** makes expanding an *empty* array
an unbound-variable error, and `"${REASONS[@]}"` on the record-tiers line is empty on any run
without /tmp/reasons.json — i.e. almost every run. That would have died after `mark_published`
but before archive and the state push: stories burned as published, labels lost. Use
`${arr[@]+"${arr[@]}"}` in these scripts.

**How to apply:** write /tmp/picks.json, then run the script — ideally in a fresh session,
since the ranking sheet is dead weight afterwards. `--dry-run` composes and changes no state.
`python3 run_tests.py` now covers both aborts (shell syntax, and unguarded empty-array
expansion under `set -u`), so an abort is news worth reporting rather than routing around.
See [[breakfast-briefing]] for the pipeline and [[briefing-cap-drops-get-marked]] for why the
order after publish is load-bearing.
