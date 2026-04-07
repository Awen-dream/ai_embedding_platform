# Redis Stream 本地联调 Runbook

## 1. 目标

本 runbook 用于验证 `task-orchestrator + Redis Stream + embedding runtime + vector-store-proxy` 的本地端到端链路是否可用。

验证目标包括：

- `task-orchestrator` 能成功连接 Redis Stream consumer group
- 通过 `gateway` 创建异步 embedding 任务
- 任务能完成 `preprocess -> embedding -> vector upsert`
- 检索服务能基于刚写入的数据返回命中结果
- `/internal/queue/stats` 返回正确的队列后端语义
- Redis stream 和死信 stream 可被本地检查

## 2. 前置条件

需要先安装项目依赖：

```bash
pip install -e .
pip install -e .[queue-redis]
```

需要本地可用的 Docker 和 Docker Compose。

## 3. 启动顺序

### 3.1 启动 broker

```bash
make broker-up
```

可选检查：

```bash
make smoke-redis-streams
```

### 3.2 启动平台服务

建议依次启动以下服务：

```bash
make run-embedding-runtime
make run-preprocess
make run-vector-store-proxy
make run-retrieval
make run-task-orchestrator-redis
make run-gateway
```

如果你更喜欢单独脚本，也可以直接运行：

- [run_embedding_runtime.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_embedding_runtime.sh)
- [run_preprocess.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_preprocess.sh)
- [run_vector_store_proxy.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_vector_store_proxy.sh)
- [run_retrieval.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_retrieval.sh)
- [run_task_orchestrator_redis.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_task_orchestrator_redis.sh)
- [run_gateway.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/run_gateway.sh)

## 4. 执行 smoke

服务起来后，执行：

```bash
make smoke-redis-task-flow
```

也可以使用更明确的别名：

```bash
make smoke-redis-e2e
```

该脚本会自动完成：

- 检查各服务 `readyz`
- 通过 `gateway` 创建异步 embedding 任务
- 轮询任务状态直到 `succeeded` 或 `failed`
- 通过 `gateway` 发起检索，确认至少返回 1 条命中
- 拉取 `/internal/queue/stats`
- 检查 Redis 主 stream 和 DLQ stream 的长度

脚本位置：

- [smoke_redis_task_flow.sh](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/scripts/local/smoke_redis_task_flow.sh)

## 5. 预期结果

理想情况下你会看到：

- 任务状态从 `queued` 进入 `running` 相关中间态，最终变为 `succeeded`
- retrieval 返回 `hits >= 1`
- `queue_backend=redis_stream`
- `delivery_semantics=at_least_once`
- `queue_depth_mode=exact`
- `dead_letter_count_mode=exact`
- 主 stream 在任务完成后长度趋近于 `0`
- DLQ stream 长度保持 `0`

## 6. 常见排查

### 任务长期停留在 `queued`

优先检查：

- `task-orchestrator` 是否以 Redis 版本启动
- `APP_QUEUE_BACKEND` 是否为 `redis_stream`
- Redis 容器是否健康

### 任务进入 `failed`

优先检查：

- `embedding-runtime`、`preprocess`、`vector-store-proxy` 是否可访问
- `task-orchestrator` 日志中的 `error_code`
- Redis 死信 stream 长度是否增加

### queue stats 正常但任务无结果

优先检查：

- `gateway` 是否正确把任务转发到了 `task-orchestrator`
- `vector-store-proxy` 是否接受到了 upsert 请求
- `task-orchestrator` 是否有 worker 运行

## 7. 收尾

联调结束后可关闭 broker：

```bash
make broker-down
```
