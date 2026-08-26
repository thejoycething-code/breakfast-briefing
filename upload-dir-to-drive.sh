#!/bin/sh
# Upload a local directory to its own folder inside the state_sync Drive folder, OUTSIDE the
# 18-file sync list so nothing in it can be mistaken for live state.
#   usage: sh upload_dir.sh <local-dir> <drive-folder-name>
# Idempotent: reuses the folder and PATCHes existing files rather than creating duplicates.
# Content goes straight from disk to Drive, so nothing passes through a model.
set -e
DIR="$1"; NAME="$2"
[ -d "$DIR" ] || { echo "no such directory: $DIR"; exit 1; }
[ -n "$NAME" ] || { echo "usage: upload_dir.sh <local-dir> <drive-folder-name>"; exit 1; }
HERE="$HOME/Downloads/breakfast-briefing"
PARENT="1X-t1k8N5XYpQHbE4PbveZ_BAoAdarV_i"
. "$HERE/gdrive_auth.sh"
TOKEN="$(bb_mint_token)"
[ -n "$TOKEN" ] || { echo "no token"; exit 1; }

ctype_for() {
  case "$1" in
    *.gz)   echo "application/gzip" ;;
    *.json) echo "application/json" ;;
    *.zip)  echo "application/zip" ;;
    *)      echo "text/plain; charset=UTF-8" ;;
  esac
}

q="name='$NAME' and '$PARENT' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
FID=$(curl -s -G "https://www.googleapis.com/drive/v3/files" -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=$q" --data-urlencode "fields=files(id)" \
  --data-urlencode "supportsAllDrives=true" | jq -r '.files[0].id // empty')
if [ -z "$FID" ]; then
  FID=$(curl -s -X POST "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "$(jq -n --arg n "$NAME" --arg p "$PARENT" \
        '{name:$n, parents:[$p], mimeType:"application/vnd.google-apps.folder"}')" \
    | jq -r '.id // empty')
  echo "created folder $NAME ($FID)"
else
  echo "reusing folder $NAME ($FID)"
fi
[ -n "$FID" ] || { echo "could not create folder"; exit 1; }

for path in "$DIR"/*; do
  [ -f "$path" ] || continue
  f=$(basename "$path"); ct=$(ctype_for "$f")
  id=$(curl -s -G "https://www.googleapis.com/drive/v3/files" -H "Authorization: Bearer $TOKEN" \
       --data-urlencode "q=name='$f' and '$FID' in parents and trashed=false" \
       --data-urlencode "fields=files(id)" --data-urlencode "supportsAllDrives=true" \
       | jq -r '.files[0].id // empty')
  if [ -n "$id" ]; then
    resp=$(curl -s -X PATCH \
      "https://www.googleapis.com/upload/drive/v3/files/$id?uploadType=media&supportsAllDrives=true&fields=id,size" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: $ct" --data-binary "@$path")
  else
    resp=$(curl -s -X POST \
      "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id,size" \
      -H "Authorization: Bearer $TOKEN" \
      -F "metadata=$(jq -n --arg n "$f" --arg p "$FID" '{name:$n, parents:[$p]}');type=application/json;charset=UTF-8" \
      -F "file=@$path;type=$ct")
  fi
  remote=$(printf '%s' "$resp" | jq -r '.size // empty')
  local_sz=$(wc -c <"$path" | tr -d ' ')
  if [ -n "$(printf '%s' "$resp" | jq -r '.id // empty')" ]; then
    if [ "$remote" = "$local_sz" ] || [ -z "$remote" ]; then
      echo "  $f: uploaded $local_sz bytes ($ct)"
    else
      echo "  $f: SIZE MISMATCH local=$local_sz drive=$remote" >&2
    fi
  else
    printf '%s' "$resp" | jq -r '.error.message // .' >&2; echo "  $f: FAILED" >&2
  fi
done
echo "folder: https://drive.google.com/drive/folders/$FID"
