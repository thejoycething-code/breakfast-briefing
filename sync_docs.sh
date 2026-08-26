#!/usr/bin/env bash
# Copy the two things that live OUTSIDE this repo into it, so they are version-controlled:
#
#   ~/.claude/scheduled-tasks/breakfast-briefing/SKILL.md   -> task/SKILL.md
#   ~/.claude/projects/<project>/memory/                    -> memory/
#
#   ./sync_docs.sh            # pull live -> repo (run this before committing)
#   ./sync_docs.sh check      # exit 1 if the repo copy has drifted. Changes nothing.
#   ./sync_docs.sh restore    # copy repo -> live. For recovering a lost file.
#
# Why copies and not symlinks (26.08.2026). A symlink would keep the two in step for free,
# and that is exactly how the five scripts were lost on 20.08.2026: a `cp` followed a symlink
# and overwrote them with an older copy, and the Drive push was the only thing that got them
# back. These two are the least replaceable files in the whole setup - SKILL.md is weeks of
# Chris's dated corrections and memory/ cannot be rebuilt from anything - so they get plain
# copies and an explicit, auditable step, not a link that some other tool can write through.
#
# The cost of copies is drift: the tracked copy goes stale and you believe you have a backup
# you do not. `check` is what makes that loud instead of silent. It is deliberately NOT wired
# into run_tests.py - memory/ is rewritten by Claude across sessions, so the fixture would go
# red constantly for reasons that have nothing to do with the pipeline, in the one place a red
# fixture is supposed to mean "a scoring change broke something".
set -euo pipefail
cd "$(dirname "$0")"
REPO="$PWD"

MODE="${1:-pull}"

LIVE_SKILL="$HOME/.claude/scheduled-tasks/breakfast-briefing/SKILL.md"
# The memory path embeds the project directory name, so it is derived, not hard-coded: if the
# project is ever moved or renamed this fails loudly rather than silently syncing nothing.
LIVE_MEM="$HOME/.claude/projects/-Users-chrisjoyce-Downloads-clacton-vercel/memory"

for p in "$LIVE_SKILL" "$LIVE_MEM"; do
    if [[ -L "$p" ]]; then
        echo "REFUSING: $p is a symlink. This script must only ever copy real files;" >&2
        echo "see the 20.08.2026 note in the header." >&2
        exit 3
    fi
done
[[ -f "$LIVE_SKILL" ]] || { echo "missing: $LIVE_SKILL" >&2; exit 3; }
[[ -d "$LIVE_MEM"   ]] || { echo "missing: $LIVE_MEM" >&2; exit 3; }

case "$MODE" in
pull)
    mkdir -p task memory
    cp "$LIVE_SKILL" task/SKILL.md
    # --delete equivalent: clear first, so a memory file deleted upstream stops being tracked.
    rm -f memory/*.md
    cp "$LIVE_MEM"/*.md memory/
    echo "pulled: task/SKILL.md ($(wc -c <task/SKILL.md | tr -d ' ') bytes)"
    echo "pulled: memory/ ($(ls -1 memory/*.md | wc -l | tr -d ' ') files)"
    ;;
check)
    rc=0
    if ! diff -q "$LIVE_SKILL" task/SKILL.md >/dev/null 2>&1; then
        echo "DRIFT: task/SKILL.md differs from $LIVE_SKILL"; rc=1
    fi
    if ! diff -rq "$LIVE_MEM" memory --exclude='.*' >/dev/null 2>&1; then
        echo "DRIFT: memory/ differs from $LIVE_MEM"
        diff -rq "$LIVE_MEM" memory --exclude='.*' 2>&1 | sed 's/^/  /' || true
        rc=1
    fi
    [[ $rc -eq 0 ]] && echo "in sync" || echo "run ./sync_docs.sh to update the repo copy"
    exit $rc
    ;;
restore)
    # Deliberately noisy and one-directional. Restoring overwrites the LIVE files, which is
    # the destructive direction, so it names what it is about to touch first.
    echo "about to overwrite:"
    echo "  $LIVE_SKILL"
    echo "  $LIVE_MEM/*.md"
    read -r -p "type 'restore' to confirm: " ans
    [[ "$ans" == "restore" ]] || { echo "aborted"; exit 1; }
    cp task/SKILL.md "$LIVE_SKILL"
    cp memory/*.md "$LIVE_MEM"/
    echo "restored from repo"
    ;;
*)
    echo "usage: $0 [pull|check|restore]" >&2
    exit 2
    ;;
esac
