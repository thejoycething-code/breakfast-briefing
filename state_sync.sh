#!/bin/bash
# Keep the pipeline's state files in Drive, so a stateless runner picks up where the last
# run left off.
#
# A cloud routine runs with persist_session:false — the container filesystem is discarded
# between runs. Everything else in the pipeline is portable (pure stdlib, no binaries), but
# these six files are memory, and without them the briefing silently degrades:
#
#   seen.json          dedupe. Lost -> the briefing repeats stories it already published.
#   cut.json           stories retired for losing to a section cap. Lost -> they come back
#                      as fresh candidates, which is the whole thing this file prevents
#                      (Chris, 18.08.2026: didn't make the first cut, not good enough for
#                      the next day). Added the day cut.json was introduced, because a
#                      stateless run would otherwise resurrect every retired story.
#   source_health.json rolling record of how many CONSECUTIVE days each source has been
#                      silent. Lost -> the counter restarts at 0 every run, never reaches
#                      the 3-day threshold, and the dead-source detector can NEVER fire.
#                      That detector exists because Live Action News was dead for an unknown
#                      period and nothing said so; in the cloud, without this file, it would
#                      be decorative. This is the one that fails quietly rather than loudly.
#   resolved.json      resolver cache. Lost -> slower, and more ugly ↗ redirects survive.
#   authors.json       byline cache. Lost -> more page fetches, some bylines missed.
#   ledes.json         article-standfirst cache for the ranking sheet. Lost -> the sheet
#                      refetches up to 150 pages instead of none; no output difference.
#   openings.json      article-text cache for the ranking sheet. Lost -> ~10 minutes of
#                      refetching, and a throttled morning reads fewer articles than it
#                      should. Carries a __schema__ key; entries under an older schema are
#                      dropped on load. Added to this list 25.08.2026 - it was created on
#                      24.08 and went a day unsynced.
#   previews.json      paywalled-preview cache, same shape and same cost. Added 25.08.2026.
#
# tiers.json rides with the JUDGEMENT files, not the state ones, and the distinction is the
# point: a cache can be rebuilt by refetching, but the tier store is an accumulated record of
# what was decided about ~1,000 stories a day and cannot be recovered from anything. Losing it
# does not slow a run down - it silently makes every story look unjudged again.
#
# Drive is the right home: the run already holds a Drive credential in order to publish, the
# state sits beside the output it describes, and no extra service is involved.
#
# It also carries JUDGEMENT_FILES (see below): Chris's hand-written testcases, exclusions,
# bylines, link fixes and source lists. Those are backup rather than state - they are the only
# irreplaceable files here, and before 19.08.2026 they had no copy outside ~/Downloads.
#
# Usage:
#   ./state_sync.sh pull      fetch state from Drive; judgement files only if absent locally
#   ./state_sync.sh push      upload every local file, replacing the Drive copy
#   ./state_sync.sh status    show both sides, change nothing
#
# Order in an unattended run:  pull -> sweep/compose/publish -> mark_published.py -> push
# Never push unless mark_published.py ran against a VERIFIED doc. Pushing an unmarked
# seen.json throws the day away; pushing a marked one for a doc that failed to publish burns
# those stories permanently.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/gdrive_auth.sh"

# State lives in the briefing folder by default. Set BB_STATE_FOLDER to keep it elsewhere.
FOLDER="${BB_STATE_FOLDER:-$BB_STATE_FOLDER_DEFAULT}"
STATE_FILES="seen.json cut.json source_health.json resolved.json authors.json ledes.json \
             openings.json previews.json firstseen.json"
# firstseen.json added 08.09.2026. It records when an UNDATED item was first offered, which is
# the only thing that stops a dateless source's whole index counting as new every single day -
# seen.json cannot, because it only ever knows what was published. Losing it would silently
# reopen that hole rather than break anything loudly, and it can only be rebuilt from the
# archive (backfill_firstseen.py), so it belongs here rather than being treated as a cache.

# Chris's own judgements, added 19.08.2026. These are NOT state - nothing in the pipeline
# writes them, he does - and they are the only files here that could not be reconstructed:
# testcases.txt is weeks of accumulated corrections as executable assertions, exclusions.txt
# is his reasoning about what the briefing will not cover, sources.opml and extra_feeds.txt
# are the source list itself. Until now they existed in exactly one place, ~/Downloads, with
# no copy anywhere.
#
# Ownership is the reason they are a separate list rather than more STATE_FILES. State is
# machine-written and Drive is authoritative between runs, so pulling it is always right.
# These are human-written and LOCAL is authoritative, so pull only bootstraps a machine that
# has none - see the pull block. Pushing them is a backup and always safe.
JUDGEMENT_FILES="testcases.txt exclusions.txt bylines.txt link_fixes.txt extra_feeds.txt \
                 sources.opml tiers.json rank_eval_log.txt repeat_eval_log.txt"

# rank_eval_log.txt and repeat_eval_log.txt added 31.08.2026: neither had ever been backed up
# by any of the three lists. The second was found by the test written to stop the first
# recurring - shortlist.py:1764 cites repeat_eval_log.txt by name ("see repeat_eval_log.txt
# for what each change moved"), so the code depended on a file nothing preserved.
# It is the accumulated before/after measurement of every scoring change ever made - the only
# thing that stops the next one being argued from a remembered example, which is the whole
# reason rank_eval.py exists. It cannot be rebuilt: replaying it would need every historical
# version of importance(). The gap was invisible to the fixture because
# test_all_scripts_backed_up only walks .py and .sh, so a missing .txt raised nothing.

# The classifier itself, added 19.08.2026 at Chris's request. testcases.txt was already
# backed up, but the patterns those assertions constrain were not - so a lost disk would
# have left the fixture describing rules that no longer existed, which is the worse half of
# the pair to lose. run_tests.py comes along because a fixture with no runner proves nothing.
# Treated as judgement, not state: hand-written, LOCAL authoritative, pull only bootstraps.
# regions.py and compose.py joined the list the same afternoon: testcases.txt asserts against
# all four (REGION cases hit regions.py, OUTLET/PAYWALLED/BYLINE cases hit compose.py's
# OUTLET_FIXES and COMMENTARY_OUTLETS, which are Chris's naming judgements and nothing else).
# Backing up a fixture without the code it constrains protects the wrong half.
# The Drive uploaders, added 20.08.2026. upload-archive-to-drive.sh is called by Step 9 of the
# scheduled task, so if it goes missing the morning run fails at the last step until someone
# rewrites it; upload-dir-to-drive.sh is the general form used for the snapshot and sweep
# folders. Both are shell rather than Python, which the push handles - only .json files get the
# validity check, everything else goes as text.
# state_sync.sh and gdrive_auth.sh added 20.08.2026, and they are a different kind of entry
# from everything else here. The rest of this list is recoverable-with-effort; these two ARE
# the recovery path. Without them the backup still exists in Drive but is unreachable without
# rewriting the auth and sync logic from scratch, which is the one failure mode a backup is
# supposed to rule out. Yes, state_sync.sh pushes itself - reading its own file while running
# is harmless, and pull never overwrites a code file that exists locally.
#
# Neither contains a credential. gdrive_auth.sh references ~/.config/breakfast-briefing/
# oauth.json (or sa.json, or BB_CLIENT_ID/BB_CLIENT_SECRET/BB_REFRESH_TOKEN) and the field
# names inside it, nothing more - checked before adding. The credential file itself is
# deliberately NOT backed up here and must not be: uploading a refresh token to the Drive
# that token unlocks is circular, and would put the key in the box it opens.
# Completed 20.08.2026: every .py and .sh in the directory is now here. The list had grown in
# tiers - classifier, then uploaders, then the auth/sync pair - each addition justified against
# how hard that file would be to rebuild. Enumerating the rest ends the argument and, more
# usefully, ends the drift: a script added later is now the exception that stands out, rather
# than one more quiet gap nobody notices until the disk goes.
#
# NOT here, deliberately: ~/.config/breakfast-briefing/oauth.json and sa.json. See the note
# above - a credential does not go in the box it opens.
CODE_FILES="shortlist.py run_tests.py regions.py compose.py fetch_feeds.py resolve.py \
            tiers.py record_tiers.py finish_edition.sh history.py repeat_eval.py \
upload-archive-to-drive.sh upload-dir-to-drive.sh state_sync.sh gdrive_auth.sh \
archive_day.py audit_feeds.py authors.py check_sources.py discover_feeds.py \
mark_published.py publish.sh rank_eval.py slice_shortlist.py \
textsignals.py tier_model.py sync_docs.sh backfill_firstseen.py"
# backfill_firstseen.py added 08.09.2026 - the "script added later" the note above predicts.
# sync_docs.sh added 26.08.2026, and archive_day.py de-duplicated in the same edit - it was
# listed twice, so every push uploaded it twice. sync_docs.sh is the script that copies
# ~/.claude's SKILL.md and memory/ into the repo; it was written straight into ~/Downloads and
# was therefore backed up nowhere, which is the exposure this list exists to close, and it is
# precisely the "script added later" the note above says should stand out.
# textsignals.py and tier_model.py added 24.08.2026 with options 1/3/4/5. They were written
# straight into ~/Downloads and were therefore backed up NOWHERE - the same exposure that made
# CODE_FILES exist in the first place, after a cp following a symlink overwrote five scripts on
# 20.08.2026 and this push was the only copy that survived.
ALL_FILES="$STATE_FILES $JUDGEMENT_FILES $CODE_FILES"

is_judgement() {
  case " $JUDGEMENT_FILES $CODE_FILES " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}
is_json() { case "$1" in *.json) return 0 ;; *) return 1 ;; esac; }
ACTION="${1:-status}"

die() { echo "state_sync.sh: $*" >&2; exit 1; }
count() { python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1])); print(len(d))
except Exception:
    try:
        # Not JSON: the judgement files are text, so report meaningful lines instead of '?'.
        n=sum(1 for l in open(sys.argv[1],encoding='utf-8',errors='replace')
              if l.strip() and not l.lstrip().startswith('#'))
        print(n)
    except Exception: print('?')" "$1" 2>/dev/null || echo '?'; }

MODE="$(bb_mode)"
[ -n "$MODE" ] || { echo "state_sync.sh: no Drive credential configured." >&2; bb_auth_hint >&2; exit 1; }
TOKEN="$(bb_mint_token)"
[ -n "$TOKEN" ] || die "could not mint an access token in mode '$MODE'"

rc=0
case "$ACTION" in
  status)
    echo "state_sync.sh (mode: $MODE, folder: $FOLDER)"
    for f in $ALL_FILES; do
      id="$(bb_file_id "$f" "$FOLDER" "$TOKEN")"
      loc="absent"; [ -f "$HERE/$f" ] && loc="$(wc -c <"$HERE/$f" | tr -d ' ') bytes / $(count "$HERE/$f") entries"
      rem="absent"
      [ -n "$id" ] && rem="$(curl -s -G "https://www.googleapis.com/drive/v3/files/$id" \
            -H "Authorization: Bearer $TOKEN" --data-urlencode "fields=size,modifiedTime" \
            --data-urlencode "supportsAllDrives=true" | jq -r '"\(.size) bytes, \(.modifiedTime)"')"
      printf "  %-20s local: %-34s drive: %s\n" "$f" "$loc" "$rem"
    done
    ;;

  pull)
    for f in $ALL_FILES; do
      # A judgement file is only ever pulled to BOOTSTRAP a machine that has none. Chris
      # edits these by hand, so the local copy is authoritative: overwriting testcases.txt
      # from a day-old Drive copy would silently revert a correction he had just written,
      # which is the exact failure the file exists to prevent.
      if is_judgement "$f" && [ -s "$HERE/$f" ]; then
        echo "  $f: present locally — not overwriting a judgement file (local wins)"
        continue
      fi
      id="$(bb_file_id "$f" "$FOLDER" "$TOKEN")"
      if [ -z "$id" ]; then
        echo "  $f: not in Drive yet — keeping local copy as the baseline"
        continue
      fi
      tmp="$(mktemp)"
      if ! curl -s -f -G "https://www.googleapis.com/drive/v3/files/$id" \
             -H "Authorization: Bearer $TOKEN" --data-urlencode "alt=media" \
             --data-urlencode "supportsAllDrives=true" -o "$tmp"; then
        rm -f "$tmp"; echo "  $f: DOWNLOAD FAILED — local copy left untouched" >&2; rc=1; continue
      fi
      # Validate before overwriting. seen.json and source_health.json only ever grow, so a
      # sharply smaller remote copy means something is wrong, not that state moved on.
      if python3 - "$tmp" "$HERE/$f" "$f" <<'PY'
import json,os,sys
new,cur,name=sys.argv[1],sys.argv[2],sys.argv[3]
if not name.endswith(".json"):
    # Judgement files are text, not JSON. json.load would raise here and reject every pull,
    # so validate what actually matters: that the download is not empty or an error page.
    body=open(new,encoding="utf-8",errors="replace").read()
    if not body.strip(): raise SystemExit("empty")
    if body.lstrip()[:1] == "<" and not name.endswith(".opml"):
        raise SystemExit("looks like an HTML error page, not %s" % name)
    raise SystemExit(0)
d=json.load(open(new))
if not isinstance(d,(dict,list)) or len(d)==0: raise SystemExit("empty")
if name in ("seen.json","cut.json","source_health.json") and os.path.exists(cur):
    old=json.load(open(cur))
    if len(d) < len(old)*0.9:
        raise SystemExit("remote %d vs local %d entries — refusing >10%% shrink" % (len(d),len(old)))
PY
      then
        mv "$tmp" "$HERE/$f"; echo "  $f: pulled $(count "$HERE/$f") entries"
      else
        rm -f "$tmp"; echo "  $f: REJECTED by validation — local copy left untouched" >&2; rc=1
      fi
    done
    ;;

  push)
    for f in $ALL_FILES; do
      [ -s "$HERE/$f" ] || { echo "  $f: absent locally, skipping"; continue; }
      # JSON validity is a real guard for state files - a truncated seen.json would be worse
      # in Drive than absent - but it is meaningless for the text judgement files, and
      # applying it to them refused every push.
      if is_json "$f" \
         && ! python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$HERE/$f" 2>/dev/null; then
        echo "  $f: NOT VALID JSON — refusing to push" >&2; rc=1; continue
      fi
      ctype="text/plain; charset=UTF-8"
      is_json "$f" && ctype="application/json"
      case "$f" in *.opml) ctype="text/xml; charset=UTF-8" ;; esac
      id="$(bb_file_id "$f" "$FOLDER" "$TOKEN")"
      if [ -n "$id" ]; then
        resp=$(curl -s -X PATCH \
          "https://www.googleapis.com/upload/drive/v3/files/$id?uploadType=media&supportsAllDrives=true&fields=id" \
          -H "Authorization: Bearer $TOKEN" -H "Content-Type: $ctype" \
          --data-binary "@$HERE/$f")
      else
        # keepRevisionForever is NOT set: Drive keeps 30 days of revisions by default, which
        # is the closest thing to a history these files have without a repo.
        meta=$(jq -n --arg n "$f" --arg p "$FOLDER" '{name:$n, parents:[$p]}')
        resp=$(curl -s -X POST \
          "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id" \
          -H "Authorization: Bearer $TOKEN" \
          -F "metadata=$meta;type=application/json;charset=UTF-8" \
          -F "file=@$HERE/$f;type=$ctype")
      fi
      newid=$(printf '%s' "$resp" | jq -r '.id // empty')
      if [ -n "$newid" ]; then
        echo "  $f: pushed $(wc -c <"$HERE/$f" | tr -d ' ') bytes"
      else
        printf '%s' "$resp" | jq -r '.error.message // .' >&2; echo "  $f: PUSH FAILED" >&2; rc=1
      fi
    done
    ;;

  *) die "unknown action '$ACTION' (use pull, push or status)" ;;
esac
exit $rc
