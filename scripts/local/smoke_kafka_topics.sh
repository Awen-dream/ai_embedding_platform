#!/usr/bin/env bash
set -euo pipefail

BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-127.0.0.1:9092}"

docker compose -f deploy/docker-compose/local-brokers.yml exec kafka \
  /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" --list
