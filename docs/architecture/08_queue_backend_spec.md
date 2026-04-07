# 队列后端规范

## 1. 目标

本规范用于统一 `task-orchestrator` 的异步任务队列后端实现方式，确保不同 broker 在接入时仍然遵守一致的任务语义、接口边界和运维约束。

当前规范覆盖以下后端：

- `inmemory`
- `sqlite`
- `redis_stream`
- `kafka`

后续新增 broker 时，必须复用同一套 `TaskQueue` 协议，不允许绕过编排层直接在 worker 内耦合具体中间件 SDK。

## 2. 统一协议

队列后端统一实现以下接口语义：

- `startup()`: 初始化连接、consumer group、topic 订阅等运行时资源
- `shutdown()`: 释放连接和后台资源
- `backend_info()`: 返回投递语义和统计语义
- `enqueue()`: 投递任务
- `dequeue()`: 获取下一条待处理任务
- `task_done()`: 在任务成功完成或进入终态后确认消息
- `add_dead_letter()`: 将终态失败消息写入死信存储
- `qsize()`: 返回队列深度
- `dead_letter_count()`: 返回死信数量

统一约束如下：

- 投递语义统一为 `at_least_once`
- worker 必须在 `process_queue_message()` 完成后调用 `task_done()`
- 进入 `failed` 终态前，必须先写死信记录，再确认原消息
- `qsize()` 和 `dead_letter_count()` 可以是 `exact`、`approximate` 或 `unsupported`
- 统计语义必须通过 `backend_info()` 暴露，不允许调用方自行猜测

## 3. 消息模型

`TaskQueueMessage` 是统一的跨后端消息模型，包含：

- `task_id`: 任务 ID
- `request_id`: 请求链路 ID
- `attempt`: 当前投递尝试次数
- `queue_id`: 仅供 SQLite 等本地持久化后端使用
- `receipt_handle`: broker 级确认句柄
- `backend_metadata`: broker 级附加元数据

设计原则：

- 业务字段与 broker 字段分离
- ack 所需信息只放在 `receipt_handle` 和 `backend_metadata`
- worker 层不感知 Redis/Kafka 的具体消息对象

## 4. 后端约束

### `inmemory`

- 用途：单进程开发和单元测试
- 优点：零依赖、启动快
- 局限：不持久化、不适合多实例

### `sqlite`

- 用途：本地持久化开发模式
- 优点：无需外部中间件，任务和队列都可落盘
- 局限：单机能力，吞吐和并发上限有限

### `redis_stream`

- 用途：本地联调、小规模部署、低成本任务编排
- 消息机制：`XADD` / `XREADGROUP` / `XACK` / `XDEL`
- consumer 语义：consumer group
- 死信机制：独立 dead-letter stream
- 推荐场景：当前 MVP 到生产前过渡阶段

### `kafka`

- 用途：更强的平台事件总线和多消费者组场景
- 消息机制：topic + consumer group + offset commit
- consumer 语义：手动提交 offset
- 死信机制：独立 dead-letter topic
- 推荐场景：更高吞吐、更强回放和跨域事件分发

## 5. 统计语义

`/internal/queue/stats` 返回：

- `queue_backend`
- `delivery_semantics`
- `queue_depth_mode`
- `dead_letter_count_mode`
- `queue_depth`
- `dead_letter_count`
- `worker_running`

约束如下：

- `Redis Stream` 当前返回 `exact` 队列深度和死信数量
- `Kafka` 当前返回 `approximate` 队列深度，`dead_letter_count` 为 `unsupported`
- 调用方在展示监控或告警时，必须优先参考 `*_mode` 字段

## 6. 配置规范

### 通用配置

- `APP_QUEUE_BACKEND`
- `APP_MAX_ATTEMPTS`
- `APP_RETRY_BACKOFF_SECONDS`

### `Redis Stream`

- `APP_REDIS_URL`
- `APP_REDIS_STREAM_KEY`
- `APP_REDIS_CONSUMER_GROUP`
- `APP_REDIS_CONSUMER_NAME`
- `APP_REDIS_DEAD_LETTER_STREAM_KEY`
- `APP_REDIS_BLOCK_MILLISECONDS`

### `Kafka`

- `APP_KAFKA_BOOTSTRAP_SERVERS`
- `APP_KAFKA_TOPIC`
- `APP_KAFKA_DEAD_LETTER_TOPIC`
- `APP_KAFKA_GROUP_ID`
- `APP_KAFKA_CLIENT_ID`
- `APP_KAFKA_POLL_TIMEOUT_MILLISECONDS`

## 7. 推荐落地顺序

建议后续按以下顺序执行：

1. 本地开发优先 `sqlite` 或 `redis_stream`
2. 联调环境优先 `redis_stream`
3. 平台事件总线或高吞吐分发场景再引入 `kafka`
4. 保持 `TaskQueue` 抽象不变，后端实现独立演进

## 8. 本地联调约定

本仓库已经提供本地 broker 联调资产：

- Compose 文件: [deploy/docker-compose/local-brokers.yml](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/deploy/docker-compose/local-brokers.yml)
- Redis 启动脚本: [scripts/local/run_task_orchestrator_redis.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_task_orchestrator_redis.sh)
- Kafka 启动脚本: [scripts/local/run_task_orchestrator_kafka.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_task_orchestrator_kafka.sh)
- 队列统计 smoke: [scripts/local/smoke_queue_stats.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/smoke_queue_stats.sh)
- Redis smoke: [scripts/local/smoke_redis_streams.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/smoke_redis_streams.sh)
- Kafka smoke: [scripts/local/smoke_kafka_topics.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/smoke_kafka_topics.sh)

标准本地联调顺序：

1. `make broker-up`
2. 启动 `embedding-runtime`、`preprocess`、`vector-store-proxy`
3. 启动 `task-orchestrator` 的 Redis 或 Kafka 版本
4. 调用 `/internal/queue/stats` 或 smoke 脚本确认 broker 连接状态

## 9. 后续演进项

当前规范已经覆盖统一接口、ack、死信和统计语义；后续继续增强时，仍需沿用本规范补充：

- pending message reclaim
- 延迟队列和定时重试
- poison message 隔离
- broker 健康检查
- 队列积压告警
- 多 worker consumer 身份治理
