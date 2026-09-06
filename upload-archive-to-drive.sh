#!/bin/sh
# Back up the ranking corpus - archive/<YYYYMMDD>/ - to Drive, one tarball per edition.
#
# Why per-edition and not one big tarball: archive_day.py writes a day's directory once and
# never touches it again, so each edition is immutable. That makes this incremental - a day
# already in Drive is skipped - and safe to run after every morning's publish.
#
# Why this is worth having at all: archive/ is the ONLY record of the tiers assigned to a
# day's ~1,600 candidates. /tmp/today.json and /tmp/picks.json are gone by the next morning
# and composed.json is overwritten, so an edition that is not archived is a day of labels
# lost for good - and until now the archive existed on one Mac's disk only. rank_eval.py
# scores every proposed scoring change against this corpus; lose it and there is nothing to
# argue from but one remembered example.
#
#   usage: ./upload-archive-to-drive.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
PARENT="1X-t1k8N5XYpQHbE4PbveZ_BAoAdarV_i"
. "$HERE/gdrive_auth.sh"
TOKEN="$(bb_mint_token)"
[ -n "$TOKEN" ] || { echo "no token"; exit 1; }

find_id() {  # name parent
  curl -s -G "https://www.googleapis.com/drive/v3/files" -H "Authorization: Bearer $TOKEN" \
    --data-urlencode "q=name='$1' and '$2' in parents and trashed=false" \
    --data-urlencode "fields=files(id,size)" --data-urlencode "supportsAllDrives=true"
}

FID=$(find_id "archive" "$PARENT" | jq -r '.files[0].id // empty')
if [ -z "$FID" ]; then
  FID=$(curl -s -X POST "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "$(jq -n --arg p "$PARENT" '{name:"archive", parents:[$p], mimeType:"application/vnd.google-apps.folder"}')" \
    | jq -r '.id')
  echo "created folder archive ($FID)"
else
  echo "reusing folder archive ($FID)"
fi

REPLACE=""
for a in "$@"; do case "$a" in --replace) REPLACE=1 ;; esac; done

for d in "$HERE"/archive/*/; do
  [ -d "$d" ] || continue
  day=$(basename "$d"); tgz="/tmp/$day.tar.gz"
  tar -czf "$tgz" -C "$HERE/archive" "$day"
  sz=$(wc -c <"$tgz" | tr -d ' ')
  existing=$(find_id "$day.tar.gz" "$FID")
  id=$(printf '%s' "$existing" | jq -r '.files[0].id // empty')
  remote=$(printf '%s' "$existing" | jq -r '.files[0].size // empty')
  if [ -n "$id" ] && [ -n "$remote" ] && [ "$remote" -gt 0 ] 2>/dev/null; then
    # --replace exists because the skip is by PRESENCE, not by content. An archived edition
    # is normally written once and never touched, which is what makes the incremental skip
    # safe. Re-archiving a day breaks that assumption: on 27.08.2026 the edition was
    # recomposed and re-archived after Chris's markup, and this loop then reported "already
    # in Drive" while quietly keeping the superseded tarball. That copy is what history.py
    # would be restored from, so a stale one would make tomorrow's cross-day repeat check
    # compare against an edition that was never published.
    if [ -n "$REPLACE" ]; then
      resp=$(curl -s -X PATCH \
        "https://www.googleapis.com/upload/drive/v3/files/$id?uploadType=media&supportsAllDrives=true&fields=id,size" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/gzip" \
        --data-binary "@$tgz")
      got=$(printf '%s' "$resp" | jq -r '.size // empty')
      if [ "$got" = "$sz" ]; then
        echo "  $day.tar.gz: REPLACED in Drive ($remote -> $sz bytes)"
      else
        echo "  $day.tar.gz: replace FAILED (remote still $remote bytes)"
      fi
      rm -f "$tgz"; continue
    fi
    echo "  $day.tar.gz: already in Drive ($remote bytes) - skipped"
    rm -f "$tgz"; continue
  fi
  resp=$(curl -s -X POST \
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id,size" \
    -H "Authorization: Bearer $TOKEN" \
    -F "metadata=$(jq -n --arg n "$day.tar.gz" --arg p "$FID" '{name:$n, parents:[$p]}');type=application/json;charset=UTF-8" \
    -F "file=@$tgz;type=application/gzip")
  got=$(printf '%s' "$resp" | jq -r '.size // empty')
  if [ "$got" = "$sz" ]; then
    echo "  $day.tar.gz: uploaded $sz bytes"
  else
    printf '%s' "$resp" | jq -r '.error.message // .' >&2
    echo "  $day.tar.gz: FAILED (local=$sz drive=$got)" >&2
  fi
  rm -f "$tgz"
done
echo "folder: https://drive.google.com/drive/folders/$FID"
