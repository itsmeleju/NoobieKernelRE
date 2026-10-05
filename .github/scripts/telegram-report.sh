#!/usr/bin/env bash
set -euo pipefail

STATUS="${1:-failure}"
KERNEL_ZIP="${2:-}"

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] \vert{}\vert{} [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
  echo "[!] Telegram secrets not defined. Skipping notification."
  exit 0
fi

API_URL="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

# Assemble commit metadata
COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "N/A")
COMMIT_MSG=$(git log -1 --pretty=%s 2>/dev/null || echo "N/A")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
RUN_URL="https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

if [ "$STATUS" = "success" ]; then
  EMOJI="✅"
  HEADER="*Kernel Build Succeeded*"
  ATTACHMENT_INFO="*Artifact:* \`${KERNEL_ZIP}\`"
else
  EMOJI="❌"
  HEADER="*Kernel Build Failed*"
  ATTACHMENT_INFO="*Status:* Compilation failed. Check GitHub workflow logs."
fi

MESSAGE=$(cat << EOF
${EMOJI}${HEADER}

*Repository:* \`${GITHUB_REPOSITORY}\`
*Branch:* \`${BRANCH}\`
*Commit:* [${COMMIT_HASH}](${RUN_URL}) - ${COMMIT_MSG}${ATTACHMENT_INFO}

[View Workflow Run](${RUN_URL})
EOF
)

PAYLOAD=$(jq -n \
  --arg chat_id "${TELEGRAM_CHAT_ID}" \
  --arg text "${MESSAGE}" \
  --arg thread_id "${TELEGRAM_MESSAGE_THREAD_ID:-}" \
  '{
    chat_id: $chat_id,
    text: $text,
    parse_mode: "Markdown",
    disable_web_page_preview: true
  } + (if $thread_id != "" then {message_thread_id: ($thread_id | tonumber)} else {} end)'
)

curl -s -X POST "${API_URL}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" > /dev/null

# Upload flashable ZIP directly to chat if build succeeded
if [ "$STATUS" = "success" ] && [ -n "$KERNEL_ZIP" ] && [ -f "$KERNEL_ZIP" ]; then
  FILE_SIZE_MB=$(du -m "$KERNEL_ZIP" | cut -f1)
  # Bot API allows files up to 50MB
  if [ "$FILE_SIZE_MB" -lt 50 ]; then
    echo "[*] Sending ZIP document to Telegram..."
    CURL_ARGS=(
      -F "chat_id=${TELEGRAM_CHAT_ID}"
      -F "document=@${KERNEL_ZIP}"
    )
    if [ -n "${TELEGRAM_MESSAGE_THREAD_ID:-}" ]; then
      CURL_ARGS+=(-F "message_thread_id=${TELEGRAM_MESSAGE_THREAD_ID}")
    fi
    curl -s -X POST "${API_URL}/sendDocument" "${CURL_ARGS[@]}" > /dev/null || true
  fi
fi
