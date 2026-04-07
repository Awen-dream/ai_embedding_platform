#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8080}"
TASK_ORCHESTRATOR_URL="${TASK_ORCHESTRATOR_URL:-http://127.0.0.1:8081}"
RUNTIME_URL="${RUNTIME_URL:-http://127.0.0.1:8082}"
VECTOR_STORE_URL="${VECTOR_STORE_URL:-http://127.0.0.1:8083}"
RETRIEVAL_URL="${RETRIEVAL_URL:-http://127.0.0.1:8084}"
PREPROCESS_URL="${PREPROCESS_URL:-http://127.0.0.1:8085}"
API_KEY="${API_KEY:-local-dev-key}"
TENANT_ID="${TENANT_ID:-tenant-a}"
MODEL="${MODEL:-bge-m3}"
INDEX_ID="${INDEX_ID:-demo-index}"
SEARCH_QUERY="${SEARCH_QUERY:-Redis Stream queue integration}"
SEARCH_TOP_K="${SEARCH_TOP_K:-3}"
MAX_POLLS="${MAX_POLLS:-30}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1}"

require_ready() {
  local name="$1"
  local url="$2"
  echo "checking ${name}: ${url}"
  curl -fsS "${url}" >/dev/null
}

extract_json_field() {
  local field="$1"
  python3 -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "${field}"
}

extract_hit_count() {
  python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("hits", [])))'
}

extract_first_hit_id() {
  python3 -c 'import json,sys; hits=json.load(sys.stdin).get("hits", []); print(hits[0].get("id", "") if hits else "")'
}

require_ready "gateway" "${GATEWAY_URL}/readyz"
require_ready "task-orchestrator" "${TASK_ORCHESTRATOR_URL}/readyz"
require_ready "embedding-runtime" "${RUNTIME_URL}/readyz"
require_ready "vector-store-proxy" "${VECTOR_STORE_URL}/readyz"
require_ready "retrieval" "${RETRIEVAL_URL}/readyz"
require_ready "preprocess" "${PREPROCESS_URL}/readyz"

echo "creating embedding batch task through gateway"
CREATE_RESPONSE="$(curl -fsS -X POST "${GATEWAY_URL}/v1/tasks/embedding" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: ${API_KEY}" \
  -d "{
    \"tenant_id\": \"${TENANT_ID}\",
    \"model\": \"${MODEL}\",
    \"source\": {
      \"type\": \"inline\",
      \"index_id\": \"${INDEX_ID}\",
      \"preprocess\": {
        \"chunk_size_words\": 12,
        \"overlap_words\": 3
      },
      \"items\": [
        {
          \"id\": \"doc-redis-1\",
          \"text\": \"Redis Stream queue integration validates asynchronous embedding ingestion for the platform smoke flow.\",
          \"metadata\": {\"scene\": \"redis-smoke\", \"lang\": \"zh-cn\"}
        },
        {
          \"id\": \"doc-redis-2\",
          \"text\": \"Kafka remains available for later adoption, while Redis Stream is the preferred local broker path for MVP validation.\",
          \"metadata\": {\"scene\": \"redis-smoke\", \"lang\": \"zh-cn\"}
        }
      ]
    }
  }")"

TASK_ID="$(printf '%s' "${CREATE_RESPONSE}" | extract_json_field task_id)"
if [[ -z "${TASK_ID}" ]]; then
  echo "failed to parse task_id from response:"
  printf '%s\n' "${CREATE_RESPONSE}"
  exit 1
fi

echo "created task: ${TASK_ID}"

STATUS=""
for ((i=1; i<=MAX_POLLS; i++)); do
  TASK_RESPONSE="$(curl -fsS -H "X-API-Key: ${API_KEY}" "${GATEWAY_URL}/v1/tasks/${TASK_ID}")"
  STATUS="$(printf '%s' "${TASK_RESPONSE}" | extract_json_field status)"
  PROGRESS="$(printf '%s' "${TASK_RESPONSE}" | extract_json_field progress)"
  echo "poll ${i}/${MAX_POLLS}: status=${STATUS} progress=${PROGRESS}"

  if [[ "${STATUS}" == "succeeded" ]]; then
    echo "task completed successfully"
    break
  fi

  if [[ "${STATUS}" == "failed" ]]; then
    echo "task failed:"
    printf '%s\n' "${TASK_RESPONSE}"
    exit 1
  fi

  sleep "${POLL_INTERVAL_SECONDS}"
done

if [[ "${STATUS}" != "succeeded" ]]; then
  echo "task did not finish within polling window"
  exit 1
fi

echo "queue stats"
curl -fsS "${TASK_ORCHESTRATOR_URL}/internal/queue/stats"
echo

echo "running retrieval verification through gateway"
SEARCH_RESPONSE="$(curl -fsS -X POST "${GATEWAY_URL}/v1/retrieval/search" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: ${API_KEY}" \
  -d "{
    \"tenant_id\": \"${TENANT_ID}\",
    \"index_id\": \"${INDEX_ID}\",
    \"query\": \"${SEARCH_QUERY}\",
    \"filters\": {
      \"scene\": \"redis-smoke\"
    },
    \"top_k\": ${SEARCH_TOP_K}
  }")"

HIT_COUNT="$(printf '%s' "${SEARCH_RESPONSE}" | extract_hit_count)"
FIRST_HIT_ID="$(printf '%s' "${SEARCH_RESPONSE}" | extract_first_hit_id)"
echo "retrieval hits=${HIT_COUNT} first_hit_id=${FIRST_HIT_ID}"

if [[ "${HIT_COUNT}" == "0" ]]; then
  echo "retrieval returned no hits:"
  printf '%s\n' "${SEARCH_RESPONSE}"
  exit 1
fi

echo "redis stream lengths"
"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/smoke_redis_streams.sh"
