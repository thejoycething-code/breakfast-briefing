#!/bin/bash
# Verify an ALREADY-PUBLISHED edition against /tmp/briefing.html, without publishing.
#
# Why this exists (27.09.2026). On 25.09.2026 publish.sh's link check reported 182/183 on a
# doc that was byte-exact - its bare-URL regex stopped at the ")" in utm_source=(direct) -
# and finish_edition.sh, correctly, stopped before marking. Everything after that had to be
# run by hand. `finish_edition.sh --from mark` is the resume path, and it must not weaken
# the one invariant the tail is ordered around: nothing is marked against a doc whose links
# have not verified. So resuming re-verifies the doc that is already in Drive, here, rather
# than trusting whoever typed --from.
#
# The comparison is href-to-href, whole, after unescaping and unwrapping Docs' redirector -
# the same rule publish.sh's verify uses once its own fix lands. Kept as a separate script
# so a resume never has to re-run publish.sh, which refuses a title that already exists.
#
#   ./verify_doc.sh                      verify "<today>: Breakfast Briefing"
#   ./verify_doc.sh --date 20260925      verify another day's edition
#   ./verify_doc.sh --html F             compare against another composed file
set -uo pipefail
HTML="/tmp/briefing.html"
DATE="$(date +%Y%m%d)"
while [ $# -gt 0 ]; do
  case "$1" in
    --html) HTML="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    *) echo "verify_doc.sh: unknown argument '$1'" >&2; exit 2 ;;
  esac
done
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/gdrive_auth.sh"
FOLDER="${BB_FOLDER:-$BB_FOLDER_DEFAULT}"
TITLE="$DATE: Breakfast Briefing"
die() { echo "verify_doc.sh: $*" >&2; exit 1; }

[ -s "$HTML" ] || die "$HTML is missing or empty - nothing to compare against"
[ -n "$(bb_mode)" ] || die "no credential configured. Run: ./publish.sh --check"
TOKEN=$(bb_mint_token)
[ -n "$TOKEN" ] || die "could not mint an access token"
ID=$(bb_file_id "$TITLE" "$FOLDER" "$TOKEN")
[ -n "$ID" ] || die "no doc titled \"$TITLE\" in the briefing folder - nothing was published to verify"
echo "doc: https://docs.google.com/document/d/$ID/edit"

exp=$(mktemp)
curl -s -G "https://www.googleapis.com/drive/v3/files/$ID/export" \
  -H "Authorization: Bearer $TOKEN" --data-urlencode "mimeType=text/html" \
  --data-urlencode "supportsAllDrives=true" > "$exp"
python3 "$HERE/verify_links.py" "$exp" "$HTML"
rc=$?; rm -f "$exp"
[ "$rc" = 0 ] || die "link verification FAILED - do not mark"
echo "  links verified byte-exact"
