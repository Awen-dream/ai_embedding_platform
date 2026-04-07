# task-orchestrator

异步任务编排服务，负责任务拆分、调度、重试、补偿和状态流转。

## 当前骨架能力

- `POST /internal/tasks/embedding`
- `GET /internal/tasks/{task_id}`
- `GET /internal/queue/stats`
- 任务仓储支持 `inmemory`、`sqlite`、`postgres`
- 队列后端支持 `inmemory`、`sqlite`、`redis_stream`、`kafka`
- SQLite 本地持久化任务状态与队列
- 后台 worker 消费骨架
- 基础重试与死信骨架
- 仓储接口 + 持久化模型边界
- PostgreSQL 初始化 SQL 和真实仓储实现
- 队列统一 ack / dead-letter / stats 语义
- `source.type=inline` 的真实批任务执行
- 调用 `preprocess` 做文本清洗和切块
- 调用 `embedding-runtime` 生成向量
- 调用 `vector-store-proxy` 写入索引

## 本地运行

```bash
make run-task-orchestrator
```

## PostgreSQL 资产

- 建表 SQL: [deploy/postgres/001_init.sql](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/control-plane/task-orchestrator/deploy/postgres/001_init.sql)
- 代码默认后端: `inmemory`
- 本地开发配置示例默认: `sqlite`
- 生产目标仓储后端: `postgres`
- Python 驱动安装: `pip install -e .[postgres]`

## 队列后端

- 规范文档: [docs/architecture/08_queue_backend_spec.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/08_queue_backend_spec.md)
- 本地 broker 编排: [deploy/docker-compose/local-brokers.yml](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/deploy/docker-compose/local-brokers.yml)
- Redis 依赖安装: `pip install -e .[queue-redis]`
- Kafka 依赖安装: `pip install -e .[queue-kafka]`
- `/internal/queue/stats` 会返回 `queue_backend`、`delivery_semantics`、`queue_depth_mode`、`dead_letter_count_mode`
- Redis 本地启动: `make run-task-orchestrator-redis`
- Kafka 本地启动: `make run-task-orchestrator-kafka`
