#!/usr/bin/env bash
set -euo pipefail

STATUS="${1:-failure}"
ZIP_NAME="${2:-}"
KERNEL_VERSION="${3:-unknown}"
BUILD_DURATION="${4:-unknown}"
IMAGE_SHA256="${5:-unknown}"

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
THREAD_ID="${TELEGRAM_MESSAGE_THREAD_ID:-}"

if [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]]; then
    echo "Telegram integration not configured; skipping."
    exit 0
fi

# Extra runtime masking
echo "::add-mask::${BOT_TOKEN}"
echo "::add-mask::${CHAT_ID}"

if [[ -n "$THREAD_ID" ]]; then
    echo "::add-mask::${THREAD_ID}"
fi

API="https://api.telegram.org/bot${BOT_TOKEN}"

REPO="${GITHUB_REPOSITORY:-unknown}"
RUN_ID="${GITHUB_RUN_ID:-0}"
RUN_URL="https://github.com/${REPO}/actions/runs/${RUN_ID}"

send_message() {
    local text="$1"

    local args=(
        -sS
        --fail
        --request POST
        "${API}/sendMessage"
        --data-urlencode "chat_id=${CHAT_ID}"
        --data-urlencode "text=${text}"
    )

    if [[ -n "$THREAD_ID" ]]; then
        args+=(--data-urlencode "message_thread_id=${THREAD_ID}")
    fi

    curl "${args[@]}" >/dev/null
}

send_document() {
    local file="$1"

    [[ -f "$file" ]] || return 0

    local args=(
        -sS
        --fail
        --request POST
        "${API}/sendDocument"
        -F "chat_id=${CHAT_ID}"
        -F "document=@${file}"
    )

    if [[ -n "$THREAD_ID" ]]; then
        args+=(-F "message_thread_id=${THREAD_ID}")
    fi

    curl "${args[@]}" >/dev/null
}

if [[ "$STATUS" == "success" ]]; then

    TEXT="✅ Kernel build succeeded

Repository: ${REPO}
Kernel: ${KERNEL_VERSION}
Duration: ${BUILD_DURATION}
Package: ${ZIP_NAME}
Image SHA256: ${IMAGE_SHA256}
Run: ${RUN_URL}"

    send_message "$TEXT"

    if [[ -n "$ZIP_NAME" && -f "out/$ZIP_NAME" ]]; then
        send_document "out/$ZIP_NAME"
    fi

else

    TEXT="❌ Kernel build failed

Repository: ${REPO}
Kernel: ${KERNEL_VERSION}
Run: ${RUN_URL}

The CI artifact contains build.log and error-summary.txt."

    send_message "$TEXT"

    if [[ -f "out/ci-logs/error-summary.txt" ]]; then
        gzip -c \
            "out/ci-logs/error-summary.txt" \
            > "out/ci-logs/error-summary.txt.gz"

        send_document "out/ci-logs/error-summary.txt.gz"
    fi

fi
