# task-orchestrator

异步任务编排服务，负责任务拆分、调度、重试、补偿和状态流转。

## 当前骨架能力

- `POST /internal/tasks/embedding`
- `GET /internal/tasks/{task_id}`
- `GET /internal/queue/stats`
- 内存态任务状态管理
- 内存态队列与后台 worker 消费骨架
- 基础重试与死信骨架
- `source.type=inline` 的真实批任务执行
- 调用 `preprocess` 做文本清洗和切块
- 调用 `embedding-runtime` 生成向量
- 调用 `vector-store-proxy` 写入索引

## 本地运行

```bash
make run-task-orchestrator
```
