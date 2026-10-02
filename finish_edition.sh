#!/usr/bin/env bash
# Everything after curation, as one command: compose -> publish -> verify -> mark ->
# record tiers -> archive -> back up.
#
# Why this exists (25.08.2026). The ranking sheet is ~165-250k tokens and the model must
# hold it to curate. Once /tmp/picks.json is written it is dead weight, but it rode along
# in context through all 23 remaining steps of the 25.08 run: measured at ~259k tokens of
# context per step against ~128k during curation, about 15% of the edition's whole cost for
# work that needs none of it.
#
# So the tail is a script, not a conversation. Run it in a FRESH session - it needs only
# /tmp/today.json, /tmp/picks.json and the files on disk. Nothing it does requires having
# read the sheet.
#
#   ./finish_edition.sh                       # normal run
#   ./finish_edition.sh --dry-run             # compose only, no publish, no state change
#   ./finish_edition.sh --from mark           # resume after a publish that stopped the tail
#                                             # (also: --from tiers|archive|backup)
#
# --from (27.09.2026). On 25.09.2026 publish.sh's link check misread a correct link and
# stopped the tail after the doc was already in Drive; marking, tiers, archive and both
# backups then had to be run by hand. --from skips compose and publish and resumes at the
# named step - but it FIRST re-verifies the doc that is already published (verify_doc.sh),
# so a resume can never mark against a doc whose links have not verified. The flag only
# changes where the run starts, never what it is allowed to skip checking.
#
# compose.py is ALWAYS called with --allow-reclass (Chris, 26.08.2026: "make it
# unconditional, I always check the numbers anyway"). Without it, compose refuses to build
# when a pick sits under a section the classifier disagrees with, and `set -e` stops the
# whole tail - which happened that morning, when 31 picks were deliberately off-classifier
# (27 rescued from the SUPPRESSED buckets, which have no section by definition, plus 4
# re-routed by judgement) and steps 5-9 had to be run by hand.
#
# What that costs, so nobody rediscovers it the hard way: the reclass check was the only
# thing standing between a transposed sheet line number and a Nigerian election piece filed
# under Life (17.08.2026, three times in one run). It is now a REPORT, not a gate. compose
# still prints every mismatch to stderr, and stderr is not redirected, so the list appears
# in this script's output above "composed N items" - read it before accepting the edition,
# and say in the run's final message that reclassed picks were deliberate.
#
# --allow-reclass is still accepted on the command line and does nothing, so old invocations
# and muscle memory do not trip the unknown-option guard.
#
# ORDER IS LOAD-BEARING and matches SKILL.md steps 5-9: no verified doc -> no marking ->
# no tier recording -> no archive -> no push. Every step after publish is skipped if the
# publish or its link verification fails, because marking a failed edition burns those
# stories permanently and pushing an unmarked seen.json throws the day away.
set -euo pipefail
cd "$(dirname "$0")"
ARGS="$*"

DRY=0
FROM=""
usage() { echo "usage: $0 [--dry-run] [--from mark|tiers|archive|backup]" >&2; exit 2; }
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)       DRY=1; shift ;;
        --allow-reclass) shift ;;   # now the default; accepted so old invocations still work
        --from)          [[ $# -ge 2 ]] || usage; FROM="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; usage ;;
    esac
done
case "$FROM" in
    ""|mark|tiers|archive|backup) ;;
    *) echo "--from must be one of: mark tiers archive backup" >&2; usage ;;
esac
[[ -z "$FROM" || $DRY -eq 0 ]] || { echo "--from and --dry-run do not combine" >&2; usage; }

# Step numbers for --from: a step runs when its number is at or after the resume point.
step_no() { case "$1" in mark) echo 1 ;; tiers) echo 2 ;; archive) echo 3 ;; backup) echo 4 ;; *) echo 0 ;; esac; }
START=$(step_no "$FROM")
runs() { [[ $(step_no "$1") -ge $START ]]; }

DATE="$(python3 -c "import json,datetime as dt;d=json.load(open('/tmp/today.json'));print(dt.datetime.fromisoformat(d['generated']).strftime('%Y%m%d'))")"
echo "== edition $DATE"

# Everything below is also written to logs/<date>-finish.log (02.10.2026). On 01.10 the
# compose/publish/mark output scrolled away and the only way to prove the doc was clean was
# to re-run verify_doc.sh. Appends, so a --from resume lands in the same file as the run it
# resumes. Process substitution is fine on this Mac's bash 3.2.
mkdir -p logs
LOG="logs/$DATE-finish.log"
exec > >(tee -a "$LOG") 2>&1
echo "== $(date '+%Y-%m-%d %H:%M:%S') finish_edition ${ARGS:-(no options)} (log: $LOG)"

if [[ -n "$FROM" ]]; then
    echo "== resume from '$FROM': re-verifying the published doc first"
    ./verify_doc.sh --date "$DATE"
else
mkdir -p out
echo "== compose"
# --allow-reclass is unconditional: see the header. compose's mismatch report still prints
# to stderr, so read it in the output above "composed N items" - it is a report now, not a
# gate, and a transposed index will publish rather than stop the run.
# Top five at the head of the Doc (02.10.2026): /tmp/five.json is the Slack-five spec, checked
# with `slack_five.py --pre` before this runs. Used ONLY when it is newer than today's sweep:
# indices mean a different story every day, so yesterday's spec would print five wrong
# stories without any check failing. Absent or stale, the Doc simply has no Top five.
FIVE_ARGS=()
if [[ -f /tmp/five.json && /tmp/five.json -nt /tmp/today.json ]]; then
    FIVE_ARGS=(--five /tmp/five.json)
    echo "== top five: /tmp/five.json will open the Doc"
else
    echo "== top five: no /tmp/five.json newer than today's sweep - the Doc opens without it"
fi
python3 compose.py /tmp/today.json /tmp/picks.json --no-mark --allow-reclass \
    ${FIVE_ARGS[@]+"${FIVE_ARGS[@]}"} \
    --md "out/${DATE}-breakfast-briefing.md" > /tmp/briefing.html
wc -c /tmp/briefing.html

if [[ $DRY -eq 1 ]]; then
    echo "== dry run: stopping before publish. Nothing marked, archived or pushed."
    exit 0
fi

# --verify exports the doc back and diffs every URL; it exits non-zero on any mismatch,
# and `set -e` turns that into a stop. That is deliberate: the checks below must never
# run against a doc whose links did not verify.
echo "== publish + verify"
./publish.sh --verify
fi

if runs mark; then
echo "== mark published"
python3 mark_published.py /tmp/today.json /tmp/picks.json
fi

# The judgement, not just the picks. Needs the leads manifest that --sheet writes; if
# curation was run without --leads-json there is nothing to record and we say so rather
# than silently skipping, because a missing day leaves those stories permanently "new".
if runs tiers; then
echo "== record tiers"
if [[ -f /tmp/leads.json ]]; then
    REASONS=()
    [[ -f /tmp/reasons.json ]] && REASONS=(--reasons /tmp/reasons.json)
    # Same bash 3.2 empty-array guard as the compose call above. Before this, a run with no
    # /tmp/reasons.json - i.e. almost every run - died here with "REASONS[@]: unbound
    # variable", AFTER marking but BEFORE archive and the state push: the exact split the
    # step order exists to prevent.
    python3 record_tiers.py /tmp/leads.json /tmp/picks.json --date "$DATE" ${REASONS[@]+"${REASONS[@]}"}
else
    echo "   WARNING: /tmp/leads.json missing - curation did not pass --leads-json to"
    echo "   shortlist.py, so this day's judgement is NOT recorded and every one of its"
    echo "   stories will look unjudged to a later --new-only run."
fi
fi

if runs archive; then
echo "== archive"
python3 archive_day.py /tmp/today.json /tmp/picks.json || \
    echo "   archive failed - edition is still fine, but the day's labels are lost"
fi

echo "== back up"
./state_sync.sh push || echo "   state push failed - un-backed-up until the next one"
./upload-archive-to-drive.sh || echo "   archive upload failed - labels are on this Mac only"

echo "== done: $DATE"
