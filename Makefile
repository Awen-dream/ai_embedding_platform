PYTHONPATH := packages/common/src:services/gateway/src:services/control-plane/task-orchestrator/src:services/data-plane/embedding-runtime/src:services/data-plane/preprocess/src:services/data-plane/vector-store-proxy/src:services/data-plane/retrieval/src
BROKER_COMPOSE_FILE := deploy/docker-compose/local-brokers.yml

.PHONY: run-gateway run-task-orchestrator run-task-orchestrator-redis run-task-orchestrator-kafka run-embedding-runtime run-preprocess run-vector-store-proxy run-retrieval broker-up broker-down broker-logs smoke-queue-stats smoke-redis-streams smoke-kafka-topics smoke-redis-task-flow smoke-redis-e2e test-unit

run-gateway:
	PYTHONPATH=$(PYTHONPATH) python3 -m uvicorn embedding_gateway.app:create_app --factory --host 0.0.0.0 --port 8080

run-task-orchestrator:
	PYTHONPATH=$(PYTHONPATH) python3 -m uvicorn embedding_task_orchestrator.app:create_app --factory --host 0.0.0.0 --port 8081

run-task-orchestrator-redis:
	./scripts/local/run_task_orchestrator_redis.sh

run-task-orchestrator-kafka:
	./scripts/local/run_task_orchestrator_kafka.sh

run-embedding-runtime:
	PYTHONPATH=$(PYTHONPATH) python3 -m uvicorn embedding_runtime_service.app:create_app --factory --host 0.0.0.0 --port 8082

run-preprocess:
	PYTHONPATH=$(PYTHONPATH) python3 -m uvicorn embedding_preprocess_service.app:create_app --factory --host 0.0.0.0 --port 8085

run-vector-store-proxy:
	PYTHONPATH=$(PYTHONPATH) python3 -m uvicorn embedding_vector_store_proxy.app:create_app --factory --host 0.0.0.0 --port 8083

run-retrieval:
	PYTHONPATH=$(PYTHONPATH) python3 -m uvicorn embedding_retrieval_service.app:create_app --factory --host 0.0.0.0 --port 8084

broker-up:
	docker compose -f $(BROKER_COMPOSE_FILE) up -d redis kafka

broker-down:
	docker compose -f $(BROKER_COMPOSE_FILE) down

broker-logs:
	docker compose -f $(BROKER_COMPOSE_FILE) logs -f redis kafka

smoke-queue-stats:
	./scripts/local/smoke_queue_stats.sh

smoke-redis-streams:
	./scripts/local/smoke_redis_streams.sh

smoke-kafka-topics:
	./scripts/local/smoke_kafka_topics.sh

smoke-redis-task-flow:
	./scripts/local/smoke_redis_task_flow.sh

smoke-redis-e2e:
	./scripts/local/smoke_redis_task_flow.sh

test-unit:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s services/gateway/tests -p 'test_*.py'
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s services/control-plane/task-orchestrator/tests -p 'test_*.py'
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s services/data-plane/embedding-runtime/tests -p 'test_*.py'
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s services/data-plane/preprocess/tests -p 'test_*.py'
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s services/data-plane/vector-store-proxy/tests -p 'test_*.py'
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s services/data-plane/retrieval/tests -p 'test_*.py'
