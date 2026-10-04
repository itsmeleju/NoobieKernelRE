#!/usr/bin/env bash
# Sends a build report to Telegram.
#
# Usage: telegram-report.sh <success|failure> <zip> <kernel_version> <duration_s> <image_sha256>
# Env:   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_MESSAGE_THREAD_ID (optional)
#        DEFCONFIG, GPU_DRIVER, RESUKISU (optional, shown in the report)

set -euo pipefail

STATUS="${1:-unknown}"
ZIP="${2:-}"
KERNEL_VERSION="${3:-unknown}"
DURATION="${4:-unknown}"
IMAGE_SHA256="${5:-unknown}"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "[!] Telegram secrets are not set, skipping report."
  exit 0
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
RUN_URL="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-unknown}/actions/runs/${GITHUB_RUN_ID:-0}"

html_escape() {
  local s="${1:-}"
  s="${s//&/&amp;}"
  s="${s//</&lt;}"
  s="${s//>/&gt;}"
  printf '%s' "${s}"
}

format_duration() {
  local d="${1:-}"
  if [[ "${d}" =~ ^[0-9]+$ ]]; then
    printf '%dm %02ds' $((d / 60)) $((d % 60))
  else
    printf '%s' "${d}"
  fi
}

# Optional forum topic
thread_args=()
if [ -n "${TELEGRAM_MESSAGE_THREAD_ID:-}" ]; then
  thread_args=(--form-string "message_thread_id=${TELEGRAM_MESSAGE_THREAD_ID}")
fi

tg_call() {
  local method="$1"
  shift
  curl -fsS --max-time 300 \
    --form-string "chat_id=${TELEGRAM_CHAT_ID}" \
    ${thread_args[@]+"${thread_args[@]}"} \
    "$@" \
    "${API}/${method}" > /dev/null
}

if [ "${STATUS}" = "success" ]; then
  HEADER="✅ <b>Build succeeded</b>"
else
  HEADER="❌ <b>Build failed</b>"
fi

MESSAGE="$(
  printf '%s\n' \
    "${HEADER}" \
    "" \
    "<b>Kernel:</b> <code>$(html_escape "${KERNEL_VERSION}")</code>" \
    "<b>Defconfig:</b> <code>$(html_escape "${DEFCONFIG:-unknown}")</code>" \
    "<b>GPU driver:</b> <code>$(html_escape "${GPU_DRIVER:-unknown}")</code>" \
    "<b>ReSukiSU:</b> <code>$(html_escape "${RESUKISU:-unknown}")</code>" \
    "<b>Duration:</b> <code>$(html_escape "$(format_duration "${DURATION}")")</code>" \
    "<b>Image SHA256:</b> <code>$(html_escape "${IMAGE_SHA256}")</code>" \
    "<b>Commit:</b> <code>$(html_escape "${GITHUB_SHA:0:7}")</code>" \
    "" \
    "<a href=\"${RUN_URL}\">View workflow run</a>"
)"

if [ "${STATUS}" = "success" ] && [ -n "${ZIP}" ] && [ -f "${ZIP}" ]; then
  tg_call sendDocument \
    --form-string "caption=${MESSAGE}" \
    --form-string "parse_mode=HTML" \
    -F "document=@${ZIP}" \
    || echo "[!] Telegram sendDocument failed."
else
  tg_call sendMessage \
    --form-string "text=${MESSAGE}" \
    --form-string "parse_mode=HTML" \
    --form-string "disable_web_page_preview=true" \
    || echo "[!] Telegram sendMessage failed."

  if [ "${STATUS}" != "success" ] && [ -f build.log ]; then
    tg_call sendDocument \
      --form-string "caption=Build log" \
      -F "document=@build.log" \
      || echo "[!] Telegram log upload failed."
  fi
fi

echo "[✓] Telegram report sent (${STATUS})."
