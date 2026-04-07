#!/usr/bin/env bash
set -euo pipefail

REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
REDIS_CLI_HOST="${REDIS_CLI_HOST:-127.0.0.1}"
REDIS_CLI_PORT="${REDIS_CLI_PORT:-6379}"
STREAM_KEY="${STREAM_KEY:-embedding:tasks}"
DLQ_STREAM_KEY="${DLQ_STREAM_KEY:-embedding:tasks:dlq}"

echo "PING"
redis-cli -h "${REDIS_CLI_HOST}" -p "${REDIS_CLI_PORT}" ping
echo "XLEN ${STREAM_KEY}"
redis-cli -h "${REDIS_CLI_HOST}" -p "${REDIS_CLI_PORT}" xlen "${STREAM_KEY}"
echo "XLEN ${DLQ_STREAM_KEY}"
redis-cli -h "${REDIS_CLI_HOST}" -p "${REDIS_CLI_PORT}" xlen "${DLQ_STREAM_KEY}"
