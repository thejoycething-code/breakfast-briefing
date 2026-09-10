#!/usr/bin/env bash
# Weekly: replay both scorers against the whole archive and log what moved.
#
# Chris, 10.09.2026. Why this exists. rank_eval.py and repeat_eval.py are explicitly barred
# from the morning path - rank_eval's own header says "Do not run rank_eval as part of the
# morning briefing; it is for sessions that change scoring" - which is right, because they
# read every archived edition and the 6am path has a deadline. The consequence nobody
# arranged for is that NOTHING ever ran them: on 10.09.2026 rank_eval_log.txt had not been
# written since 31.08 and repeat_eval_log.txt since 28.08, while the corpus they score
# against had grown from 4 archived editions to 18. Two eval corpora, paid for daily by
# archive_day.py, sitting idle.
#
# So: a weekly job, deliberately NOT wired into finish_edition.sh.
#
#   ./eval_week.sh              # run both, append to the logs
#   ./eval_week.sh --dry-run    # run both, print, append nothing
#
# What to do with the output. Neither number is a target and neither is a gate:
#
#   - rank_eval's concordance measures AGREEMENT WITH PAST PICKS, not correctness. Its own
#     header proves the trap: on 18.08.2026 a bug that correlated with a favoured beat scored
#     well. A change that promotes stories the curator FAILED to pick must show concordance
#     flat or DOWN, because those stories are labelled 0 in the archive - that is what
#     happened on 31.08 and it was the expected result, not a null one.
#   - so read the trend, and read t1-recall alongside it. Concordance rising while t1-recall
#     falls is the scorer learning to agree with the curator's misses.
#   - testcases.txt keeps veto power over both.
#
# It does not fail on a bad number, because there is no such thing here - only a number worth
# looking at. It fails only if a scorer crashes, which is a real regression.
set -uo pipefail
cd "$(dirname "$0")"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

NOTE="${BB_EVAL_NOTE:-weekly scheduled re-scan, $(date -u +%Y-%m-%d)}"
EDITIONS=$(ls -d archive/2* 2>/dev/null | wc -l | tr -d ' ')

echo "== eval_week: $EDITIONS archived edition(s), note: $NOTE"
if [ "$EDITIONS" -lt 2 ]; then
    echo "   fewer than 2 editions archived - nothing to replay against, stopping."
    exit 0
fi

rc=0

# A non-zero exit from these two does NOT mean the scorer broke. repeat_eval.py exits 1 when
# a GOLD case fails, and a gold case failing is the normal state here: testcases.txt is
# written red-first, so the cross-section case has been failing since 08.09.2026 by design.
# Treating that as a crash would make this job permanently red for the same reason
# hooks/pre-commit was (see known_red.txt) - a deliberate red disabling an unrelated signal.
# So: a Python traceback is a crash and fails the job; anything else is a score to read.
run_scorer() {
    local name="$1"; shift
    local log; log="$(mktemp)"
    echo
    echo "== $name"
    if python3 "$@" > "$log" 2>&1; then
        cat "$log"
    else
        cat "$log"
        if grep -q "Traceback (most recent call last)" "$log"; then
            echo "   ^^ $name CRASHED - that is a regression in the scorer." >&2
            rc=1
        else
            echo "   ($name exited non-zero without crashing: a failing gold case or a score" \
                 "below its own threshold. That is a number to read, not a broken scorer.)"
        fi
    fi
    rm -f "$log"
}

if [ "$DRY" = 1 ]; then
    run_scorer rank_eval.py rank_eval.py
    run_scorer repeat_eval.py repeat_eval.py --misses
else
    run_scorer rank_eval.py rank_eval.py --log "$NOTE"
    # --collisions is the half that found a real bug: on 27.08.2026 word overlap would have
    # merged 20 pairs that is_development_of blocks, and the stem/class fix took it to 1.
    # Cheap, and it is the arm most likely to rot as the archive grows.
    run_scorer repeat_eval.py repeat_eval.py --log "$NOTE" --collisions
fi

echo
if [ "$rc" != 0 ]; then
    echo "== eval_week: a scorer CRASHED. The logs are unchanged for whichever one died." >&2
    exit 1
fi
if [ "$DRY" = 1 ]; then
    echo "== eval_week: dry run, logs unchanged."
else
    echo "== eval_week: appended to rank_eval_log.txt and repeat_eval_log.txt"
    echo "   Read the trend, not the absolute number, and read t1-recall next to concordance."
fi
