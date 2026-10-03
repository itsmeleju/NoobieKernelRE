#!/usr/bin/env bash
set -euo pipefail

USER_NAME="NoobieThingZ_bot"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
API="https://api.telegram.org/bot${BOT_TOKEN}"

usage() {
  echo "Usage: $0 success|failure toolchain version gpu resukisu nomount zip_name [zip_path]"
  exit 2
}

[ "$#" -ge 7 ] && [ "$#" -le 8 ] || usage
MODE="$1"
TOOLCHAIN="$2"
VERSION="$3"
GPU="$4"
RESUKISU="$5"
NOMOUNT="$6"
ZIP_NAME="$7"
ZIP_PATH="${8:-}"

if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
  echo "::error::TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID secrets are required."
  exit 1
fi

echo "[Telegram] Checking bot connection..."
getme="$(curl -fsS --retry 2 --connect-timeout 10 --max-time 30 \
  -X POST "$API/getMe" \
  -H 'Content-Type: application/json' \
  --data '{}')" || {
    echo "::error::[Telegram] Bot connection FAILED"
    exit 1
  }

if ! python3 - "$getme" <<'PY'
import json, sys
data=json.loads(sys.argv[1])
raise SystemExit(0 if data.get("ok") else 1)
PY
then
  echo "::error::[Telegram] Bot connection FAILED"
  exit 1
fi
echo "[Telegram] Bot connection OK"

send_message() {
  local text="$1"
  local response
  response="$(curl -fsS --retry 2 --connect-timeout 10 --max-time 30 \
    -X POST "$API/sendMessage" \
    --data-urlencode "chat_id=$CHAT_ID" \
    --data-urlencode "text=$text" \
    --data-urlencode "disable_web_page_preview=true")" || {
      echo "::error::[Telegram] Message delivery FAILED"
      return 1
    }
  python3 - "$response" <<'PY'
import json, sys
data=json.loads(sys.argv[1])
raise SystemExit(0 if data.get("ok") else 1)
PY
}

send_document() {
  local file="$1"
  local caption="$2"
  [ -s "$file" ] || {
    echo "::error::[Telegram] Document is missing or empty: $file"
    return 1
  }
  local response
  response="$(curl -fsS --retry 2 --connect-timeout 10 --max-time 120 \
    -X POST "$API/sendDocument" \
    -F "chat_id=$CHAT_ID" \
    -F "document=@$file" \
    -F "caption=$caption")" || {
      echo "::error::[Telegram] Document upload FAILED"
      return 1
    }
  python3 - "$response" <<'PY'
import json, sys
data=json.loads(sys.argv[1])
raise SystemExit(0 if data.get("ok") else 1)
PY
}

case "$MODE" in
  success)
    MESSAGE="✅ Kernel Build Success!
👤 Builder: @${USER_NAME}
⚙️ Kernel: https://github.com/itsmeleju/NoobieKernelRE
📱 Device: Samsung A32 (MT6768)
🔧 Toolchain: ${TOOLCHAIN}${VERSION:+ / ${VERSION}}
🎮 GPU: ${GPU}
🧩 ReSukiSU: ${RESUKISU}
🛡️ NoMount: ${NOMOUNT}
📦 ZIP: ${ZIP_NAME}"
    send_message "$MESSAGE"
    [ -n "$ZIP_PATH" ] || {
      echo "::error::[Telegram] Success ZIP path is missing."
      exit 1
    }
    send_document "$ZIP_PATH" "NoobieKernelRE final AnyKernel3 ZIP: $ZIP_NAME"
    ;;
  failure)
    report="build-error.txt"
    if [ ! -s "$report" ]; then
      report="$(mktemp)"
      trap 'rm -f "$report"' EXIT
      {
        echo "NoobieKernelRE build failure"
        echo "Toolchain: $TOOLCHAIN${VERSION:+ / $VERSION}"
        echo "GPU: $GPU"
        echo "ReSukiSU: $RESUKISU"
        echo "NoMount: $NOMOUNT"
        echo
        echo "First meaningful compiler/linker error:"
        first=""
        if grep -n -m1 -E '(^|[[:space:]])(fatal error:|error:|undefined reference|ld\.lld: error:|collect2: error:|No rule to make target|recipe for target .+ failed|Error [0-9]+)' build.log > "${report}.first"; then
          first="$(cat "${report}.first")"
        fi
        rm -f "${report}.first"
        if [ -n "$first" ]; then
          echo "$first"
          line="${first%%:*}"
          start=$(( line > 8 ? line - 8 : 1 ))
          end=$(( line + 8 ))
          sed -n "${start},${end}p" build.log
        else
          tail -n 80 build.log
        fi
      } > "$report"
    fi
    MESSAGE="❌ Kernel Build Failed
👤 Builder: @${USER_NAME}
⚙️ Kernel: https://github.com/itsmeleju/NoobieKernelRE
📱 Device: Samsung A32 (MT6768)
🔧 Toolchain: ${TOOLCHAIN}${VERSION:+ / ${VERSION}}
🎮 GPU: ${GPU}
🧩 ReSukiSU: ${RESUKISU}
🛡️ NoMount: ${NOMOUNT}
See the attached error report/build log."
    send_message "$MESSAGE"
    send_document "$report" "NoobieKernelRE build failure report"
    ;;
  *)
    usage
    ;;
esac

echo "[Telegram] Report delivered successfully."