#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/services/control-plane/task-orchestrator/configs/dev.kafka.env.example"
export PYTHONPATH="${ROOT_DIR}/packages/common/src:${ROOT_DIR}/services/gateway/src:${ROOT_DIR}/services/control-plane/task-orchestrator/src:${ROOT_DIR}/services/data-plane/embedding-runtime/src:${ROOT_DIR}/services/data-plane/preprocess/src:${ROOT_DIR}/services/data-plane/vector-store-proxy/src:${ROOT_DIR}/services/data-plane/retrieval/src"

set -a
source "${ENV_FILE}"
set +a

exec python3 -m uvicorn embedding_task_orchestrator.app:create_app --factory --host "${APP_HOST}" --port "${APP_PORT}"
