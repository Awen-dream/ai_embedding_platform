#!/usr/bin/env bash
set -euo pipefail

QUEUE_STATS_URL="${1:-http://127.0.0.1:8081/internal/queue/stats}"

curl -sS "${QUEUE_STATS_URL}"
