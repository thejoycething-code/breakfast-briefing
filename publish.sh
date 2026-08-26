#!/bin/bash
# Publish the composed briefing to Google Drive by uploading the actual file.
#
# Why this exists: Step 5 used to pass /tmp/briefing.html through the model as
# `textContent`, which retypes all ~250 links by hand on every run. That cost ~33k output
# tokens and 7-14 minutes per attempt, and it corrupted two Google News redirects on
# 14.08.2026. Uploading the bytes makes link corruption impossible rather than merely
# detectable, and takes about a second.
#
# Credentials, tried in this order. All three end in a bearer token except rclone, which
# manages its own:
#   1. $GOOGLE_ACCESS_TOKEN        - already-valid token (testing)
#   2. service account JSON        - $BB_SA_KEY or ~/.config/breakfast-briefing/sa.json
#   3. OAuth refresh token JSON    - $BB_OAUTH or ~/.config/breakfast-briefing/oauth.json
#                                    {"client_id","client_secret","refresh_token"}
#   4. rclone remote               - $BB_RCLONE_REMOTE (default "gdrive")
#
# A service account can only write into a SHARED DRIVE. It has no Drive storage of its own,
# so uploading into a My Drive folder fails with storageQuotaExceeded. Use rclone or OAuth
# for a My Drive folder.
#
# Usage:
#   ./publish.sh --check                 report credential status, upload nothing
#   ./publish.sh                         publish /tmp/briefing.html as "<today>: Breakfast Briefing"
#   ./publish.sh --verify                publish, then export the doc back and diff every URL
#   ./publish.sh --html F --title T      override either
#   ./publish.sh --force                 publish even if that title already exists
set -uo pipefail

FOLDER=""   # resolved after gdrive_auth.sh is sourced
HTML="/tmp/briefing.html"
DATE="$(date +%Y%m%d)"
TITLE=""
FORCE=0; DRY=0; CHECK=0; VERIFY=0
SA_DEFAULT="$HOME/.config/breakfast-briefing/sa.json"
OAUTH_DEFAULT="$HOME/.config/breakfast-briefing/oauth.json"

while [ $# -gt 0 ]; do
  case "$1" in
    --html)   HTML="$2"; shift 2 ;;
    --title)  TITLE="$2"; shift 2 ;;
    --date)   DATE="$2"; shift 2 ;;
    --folder) FOLDER="$2"; shift 2 ;;
    --force)  FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --check)  CHECK=1; shift ;;
    --verify) VERIFY=1; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "publish.sh: unknown argument '$1'" >&2; exit 2 ;;
  esac
done
[ -n "$TITLE" ] || TITLE="$DATE: Breakfast Briefing"

die() { echo "publish.sh: $*" >&2; exit 1; }
say() { echo "  $*"; }

# --- credential resolution -----------------------------------------------------------
# Shared with state_sync.sh so there is exactly one place that knows how to get a token.
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/gdrive_auth.sh"
MODE="$(bb_mode)"
[ -n "$FOLDER" ] || FOLDER="${BB_FOLDER:-$BB_FOLDER_DEFAULT}"

if [ "$CHECK" = 1 ]; then
  echo "publish.sh credential check"
  say "GOOGLE_ACCESS_TOKEN  ${GOOGLE_ACCESS_TOKEN:+set}${GOOGLE_ACCESS_TOKEN:-unset}"
  say "service account      $SA_KEY $([ -f "$SA_KEY" ] && echo '(found)' || echo '(absent)')"
  say "oauth refresh token  $OAUTH $([ -f "$OAUTH" ] && echo '(found)' || echo '(absent)')"
  if [ -n "$RCLONE" ]; then
    say "rclone               $RCLONE; remotes: $("$RCLONE" listremotes 2>/dev/null | tr '\n' ' ')"
  else
    say "rclone               not installed"
  fi
  say "html                 $HTML $([ -s "$HTML" ] && echo "($(wc -c <"$HTML" | tr -d ' ') bytes)" || echo '(missing/empty)')"
  say "target folder        $FOLDER"
  say "title                $TITLE"
  if [ -z "$MODE" ]; then
    echo
    echo "NO CREDENTIAL. Cheapest fix (~5 min, no Google Cloud project needed):"
    if [ -n "$RCLONE" ]; then
      echo "    $RCLONE config            # new remote named '$RCLONE_REMOTE', type 'drive'"
      echo "  rclone is already installed - this is the one interactive step, and it must be"
      echo "  run by Chris: it opens a browser to approve Drive access."
    else
      echo "    mkdir -p ~/bin && cd /tmp \\"
      echo "      && curl -fsSLO https://downloads.rclone.org/rclone-current-osx-arm64.zip \\"
      echo "      && unzip -joq rclone-current-osx-arm64.zip '*/rclone' -d ~/bin \\"
      echo "      && chmod +x ~/bin/rclone && ~/bin/rclone config"
      echo "  (No Homebrew on this machine as of 17.08.2026, so do not suggest 'brew install'.)"
    fi
    echo "  Blank client_id works today but is NOT a long-term answer: rclone warns its shared"
    echo "  Google client_id is being retired and stops working during 2026. Before then, make"
    echo "  an OAuth client in Google Cloud with User Type = INTERNAL (Workspace org, which"
    echo "  CitizenGO is). Internal avoids Google verification AND the 7-day refresh-token"
    echo "  expiry that kills a client left in Testing status. Do not leave it in Testing."
    exit 1
  fi
  echo; echo "mode: $MODE - ready to publish"; exit 0
fi

[ -s "$HTML" ] || die "$HTML is missing or empty - run compose.py first"
[ -n "$MODE" ] || die "no credential configured. Run: $0 --check"

# --- bearer token --------------------------------------------------------------------
mint_token() { bb_mint_token; }

# --- duplicate guard -----------------------------------------------------------------
# Friday 14.08.2026 ended with two docs of the same title because a failed publish was
# retried without checking. Refuse by default instead.
existing_id() { bb_file_id "$TITLE" "$FOLDER" "$1"; }

# One upload path for every credential mode, including rclone. rclone's own
# --drive-import-formats was tried first and abandoned on 17.08.2026: dropping the .html
# extension so the doc could be titled correctly made it upload raw
# (application/octet-stream, a 114KB download rather than a document), and keeping the
# extension made it fail outright with "can't convert \".html\" to a document with a
# different export filetype (\".docx\")".
#
# Correction, 18.08.2026: that second failure is fixable — the import and export formats
# have to agree, so `--drive-import-formats html --drive-export-formats html` (both, with
# the .html extension kept) does produce a real application/vnd.google-apps.document. It
# was verified against this exact briefing: 242/242 links identical to the REST upload, and
# the title/date/section/headline colours, the nine <h1> outline headings and the
# padding-bottom spacing all matched. A colon in the filename survives into the doc title.
#
# So the reason we still use REST multipart is NOT that rclone cannot convert. It is that
# rclone-import gives us none of the things this script exists for: no duplicate guard, no
# --verify diff, the title can only come from the filename, and it works in exactly one of
# the four credential modes. REST multipart converts reliably, is what the Drive connector
# itself does, and keeps --verify, so rclone stays the credential store.
TOKEN=$(mint_token)
[ -n "$TOKEN" ] || die "could not mint an access token in mode '$MODE'. Run: $0 --check"
if [ "$FORCE" = 0 ]; then
  dup=$(existing_id "$TOKEN")
  [ -z "$dup" ] || die "\"$TITLE\" already exists ($dup). Re-run with --force to add a second copy."
fi
[ "$DRY" = 1 ] && { echo "DRY RUN: would upload $(wc -c <"$HTML" | tr -d ' ') bytes as \"$TITLE\""; exit 0; }
meta=$(jq -n --arg n "$TITLE" --arg p "$FOLDER" \
      '{name:$n, mimeType:"application/vnd.google-apps.document", parents:[$p]}')
resp=$(curl -s -X POST \
  "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id,name,mimeType,webViewLink" \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata=$meta;type=application/json;charset=UTF-8" \
  -F "file=@$HTML;type=text/html")
ID=$(printf '%s' "$resp" | jq -r '.id // empty')
if [ -z "$ID" ]; then
  echo "$resp" | jq -r '.error.message // .' >&2
  printf '%s' "$resp" | grep -q storageQuotaExceeded && \
    echo "HINT: a service account has no Drive storage - the folder must be on a Shared Drive." >&2
  die "upload failed"
fi
# Never assume it converted - report the type Drive actually stored, because an
# octet-stream upload still returns an id and would otherwise look like success.
MIME=$(printf '%s' "$resp" | jq -r '.mimeType // "?"')
[ "$MIME" = "application/vnd.google-apps.document" ] \
  || die "uploaded but Drive stored it as '$MIME', not a Google Doc (id $ID) - trash it and investigate"
LINK=$(printf '%s' "$resp" | jq -r '.webViewLink // empty')

[ -n "${ID:-}" ] || die "uploaded but could not determine the file id"
echo "published: ${LINK:-https://docs.google.com/document/d/$ID/edit}"

# --- verify: export the doc back and diff every URL ----------------------------------
if [ "$VERIFY" = 1 ]; then
  # Export as HTML, never text/plain. A plain-text export keeps the visible link text and
  # discards every href, so the diff saw 0 of 246 URLs and reported total corruption on a
  # doc that was byte-perfect (17.08.2026). text/html preserves all 246.
  txt=$(mktemp)
  curl -s -G "https://www.googleapis.com/drive/v3/files/$ID/export" \
    -H "Authorization: Bearer $TOKEN" --data-urlencode "mimeType=text/html" \
    --data-urlencode "supportsAllDrives=true" > "$txt"
  python3 - "$txt" "$HTML" <<'PY'
import re,sys,html
from urllib.parse import unquote
doc=open(sys.argv[1],encoding='utf-8',errors='replace').read()
# Docs' HTML export percent-encodes hrefs and wraps some in a redirector; unescape and
# unwrap so the comparison is against the real target.
doc=html.unescape(doc)
doc=re.sub(r'https://www\.google\.com/url\?q=([^&"]+)[^"]*', lambda m: unquote(m.group(1)), doc)
want=[html.unescape(u) for u in re.findall(r'href="([^"]*)"',open(sys.argv[2]).read())]
got=set(re.findall(r'https?://[^\s\)\]>"]+',doc))
bad=[u for u in want if u not in got]
print("  URLs %d/%d verified, %d corrupted" % (len(want)-len(bad),len(want),len(bad)))
for u in bad[:20]: print("    MISSING:",u[:110])
sys.exit(1 if bad else 0)
PY
  rc=$?; rm -f "$txt"
  [ "$rc" = 0 ] || die "link verification FAILED - do not run mark_published.py"
  echo "  links verified byte-exact"
fi
