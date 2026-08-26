# Shared Google Drive credential resolution. Sourced by publish.sh and state_sync.sh so
# there is exactly one place that knows how to obtain a bearer token.
#
# Modes, in priority order:
#   1. $GOOGLE_ACCESS_TOKEN        - already-valid token (testing, or passed between scripts)
#   2. service account JSON        - $BB_SA_KEY or ~/.config/breakfast-briefing/sa.json
#   3. OAuth refresh token JSON    - $BB_OAUTH or ~/.config/breakfast-briefing/oauth.json
#                                    {"client_id","client_secret","refresh_token"}
#   4. rclone remote               - $BB_RCLONE_REMOTE (default "gdrive")
#
# For an unattended CLOUD run use mode 3. rclone is a local convenience only: it will not
# exist in a cloud environment, and its shared Google client_id is being retired during 2026
# anyway. Mode 3 reads three values that can be supplied as environment variables, which is
# what a cloud routine can actually provide.
#
# A service account (mode 2) has no Drive storage of its own, so it can only write into a
# Shared Drive - uploading to a My Drive folder fails with storageQuotaExceeded.

BB_FOLDER_DEFAULT="1ff3EpR5ER6AxCopLDrVOlaQVlVhi2LzQ"
# Pipeline internals (state files, the code bundle) live in a subfolder, NOT beside the
# briefings. Chris asked for that on 18.08.2026 after four state files and a zip appeared
# in the folder he reads every morning. Keeping them separate also means the Step 1
# idempotency check only ever sees actual briefings.
BB_STATE_FOLDER_DEFAULT="1X-t1k8N5XYpQHbE4PbveZ_BAoAdarV_i"
SA_KEY="${BB_SA_KEY:-$HOME/.config/breakfast-briefing/sa.json}"
OAUTH="${BB_OAUTH:-$HOME/.config/breakfast-briefing/oauth.json}"
RCLONE_REMOTE="${BB_RCLONE_REMOTE:-gdrive}"

# ~/bin is not on PATH under a non-login shell such as cron or a scheduled task.
RCLONE="$(command -v rclone 2>/dev/null || true)"
[ -n "$RCLONE" ] || { [ -x "$HOME/bin/rclone" ] && RCLONE="$HOME/bin/rclone"; }

# Allow the OAuth triple to arrive purely as environment variables, with no file on disk.
# This is the cloud path: a routine can set them, but cannot drop a file in place.
if [ -z "${GOOGLE_ACCESS_TOKEN:-}" ] && [ ! -f "$OAUTH" ] \
   && [ -n "${BB_CLIENT_ID:-}" ] && [ -n "${BB_CLIENT_SECRET:-}" ] && [ -n "${BB_REFRESH_TOKEN:-}" ]; then
  OAUTH="$(mktemp)"
  chmod 600 "$OAUTH"
  jq -n --arg i "$BB_CLIENT_ID" --arg s "$BB_CLIENT_SECRET" --arg r "$BB_REFRESH_TOKEN" \
    '{client_id:$i, client_secret:$s, refresh_token:$r}' > "$OAUTH"
  BB_OAUTH_IS_TEMP=1
fi

bb_mode() {
  if   [ -n "${GOOGLE_ACCESS_TOKEN:-}" ]; then echo token
  elif [ -f "$SA_KEY" ];  then echo sa
  elif [ -f "$OAUTH" ];   then echo oauth
  elif [ -n "$RCLONE" ] && "$RCLONE" listremotes 2>/dev/null | grep -qx "${RCLONE_REMOTE}:"; then echo rclone
  else echo ""
  fi
}

bb_mint_token() {
  case "$(bb_mode)" in
    token) printf '%s' "$GOOGLE_ACCESS_TOKEN" ;;
    rclone)
      # rclone refreshes its own grant but has no "give me a token" command. A trivial API
      # call forces a refresh and rewrites rclone.conf, so what we read next is current.
      "$RCLONE" about "$RCLONE_REMOTE:" >/dev/null 2>&1
      "$RCLONE" config dump 2>/dev/null \
        | jq -r --arg r "$RCLONE_REMOTE" \
            '.[$r].token | if type=="string" then fromjson else . end | .access_token // empty' ;;
    oauth)
      jq -r '"client_id=\(.client_id)&client_secret=\(.client_secret)&refresh_token=\(.refresh_token)&grant_type=refresh_token"' "$OAUTH" \
        | curl -s -X POST https://oauth2.googleapis.com/token -d @- | jq -r '.access_token // empty' ;;
    sa)
      # Sign locally with cryptography/google.auth.crypt; exchange with curl, because no
      # Python HTTP transport (requests/urllib3) is installed.
      local assertion
      assertion=$(python3 - "$SA_KEY" <<'PY' 2>/dev/null
import json,sys,time
from google.auth import crypt, jwt
info=json.load(open(sys.argv[1]))
now=int(time.time())
payload={"iss":info["client_email"],"scope":"https://www.googleapis.com/auth/drive",
         "aud":"https://oauth2.googleapis.com/token","iat":now,"exp":now+3600}
sys.stdout.write(jwt.encode(crypt.RSASigner.from_service_account_info(info),payload).decode())
PY
) || return 1
      [ -n "$assertion" ] || return 1
      curl -s -X POST https://oauth2.googleapis.com/token \
        -d grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer \
        --data-urlencode "assertion=$assertion" | jq -r '.access_token // empty' ;;
  esac
}

# id of a file with this exact name in this folder, or empty
bb_file_id() {
  local name="$1" folder="$2" tok="$3" q
  q=$(printf "name = '%s' and '%s' in parents and trashed = false" \
        "$(printf '%s' "$name" | sed "s/'/\\\\'/g")" "$folder")
  curl -s -G "https://www.googleapis.com/drive/v3/files" \
    -H "Authorization: Bearer $tok" \
    --data-urlencode "q=$q" --data-urlencode "fields=files(id,name)" \
    --data-urlencode "supportsAllDrives=true" \
    --data-urlencode "includeItemsFromAllDrives=true" | jq -r '.files[0].id // empty'
}

bb_auth_hint() {
  echo "  For an unattended/cloud run set BB_CLIENT_ID, BB_CLIENT_SECRET and BB_REFRESH_TOKEN."
  echo "  Create the OAuth client in Google Cloud with User Type = INTERNAL (CitizenGO is a"
  echo "  Workspace org). Internal avoids Google verification AND the 7-day refresh-token"
  echo "  expiry that kills a client left in Testing status."
}
