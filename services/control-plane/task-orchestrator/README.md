# task-orchestrator

异步任务编排服务，负责任务拆分、调度、重试、补偿和状态流转。

## 当前骨架能力

- `POST /internal/tasks/embedding`
- `GET /internal/tasks/{task_id}`
- `GET /internal/queue/stats`
- 内存态任务状态管理
- 内存态队列与后台 worker 消费骨架
- 基础重试与死信骨架
- 仓储接口 + 内存实现，已为 PostgreSQL 持久化预留边界
- PostgreSQL 初始化 SQL 和仓储占位实现
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
- 当前默认后端: `inmemory`
- 预留后端: `postgres`
