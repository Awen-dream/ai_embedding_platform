# 事件模型规范

## 1. 目标

统一异步任务和跨服务集成使用的事件模型，保证：

- 事件命名稳定
- 字段结构统一
- 幂等与追踪可落地
- 可支持后续审计、回放、死信处理

本规范优先覆盖 `Phase 0` 和 `Phase 1` 所需事件。

## 2. 适用范围

首期事件主要用于：

- 异步Embedding任务流转
- 预处理完成通知
- 推理完成通知
- 向量写入完成通知
- 任务终态通知

## 3. 事件命名规范

统一格式：

`embedding.<domain>.<action>`

示例：

- `embedding.task.created`
- `embedding.task.queued`
- `embedding.preprocess.completed`
- `embedding.runtime.completed`
- `embedding.vector.upserted`
- `embedding.task.succeeded`
- `embedding.task.failed`

命名要求：

- 使用小写英文
- 使用过去分词表示已发生事件
- 事件名表达事实，不表达命令

## 4. 标准事件Envelope

所有事件消息建议统一包含 envelope：

```json
{
  "event_id": "evt_123",
  "event_type": "embedding.task.created",
  "event_version": "1.0",
  "occurred_at": "2026-04-03T11:00:00Z",
  "source": "task-orchestrator",
  "tenant_id": "tenant-a",
  "request_id": "req_123",
  "trace_id": "trace_123",
  "idempotency_key": "task_123:shard_1",
  "subject": {
    "task_id": "task_123",
    "job_id": "job_123",
    "resource_type": "embedding_task"
  },
  "data": {}
}
```

## 5. Envelope字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `event_id` | 是 | 事件唯一ID |
| `event_type` | 是 | 事件名称 |
| `event_version` | 是 | 事件版本，便于兼容升级 |
| `occurred_at` | 是 | 事件产生时间 |
| `source` | 是 | 事件来源服务 |
| `tenant_id` | 是 | 租户标识 |
| `request_id` | 否 | 来源请求ID |
| `trace_id` | 否 | 链路追踪ID |
| `idempotency_key` | 是 | 幂等键，用于避免重复消费 |
| `subject` | 是 | 事件核心对象标识 |
| `data` | 是 | 事件业务负载 |

## 6. Topic规划建议

MVP阶段可先使用以下Topic：

- `embedding.task.events`
- `embedding.preprocess.events`
- `embedding.runtime.events`
- `embedding.vector.events`

若使用Kafka，建议按 `tenant_id` 或 `task_id` 做分区键，优先保证单任务内事件局部有序。

## 7. 首批事件定义

### 7.1 `embedding.task.created`

触发方：

- `task-orchestrator`

触发时机：

- 任务请求通过校验并创建成功后

`data`字段建议：

```json
{
  "task_id": "task_123",
  "task_type": "embedding_batch",
  "model": "bge-m3",
  "modality": "text",
  "input_source": {
    "type": "object_storage",
    "uri": "s3://bucket/path/file.jsonl"
  },
  "shard_count": 8
}
```

### 7.2 `embedding.task.queued`

触发方：

- `task-orchestrator`

触发时机：

- 任务拆分完成并投递到队列后

`data`字段建议：

- `task_id`
- `shard_id`
- `queue_name`
- `attempt`

### 7.3 `embedding.preprocess.completed`

触发方：

- `preprocess`

触发时机：

- 单个分片预处理完成后

`data`字段建议：

- `task_id`
- `shard_id`
- `input_count`
- `chunk_count`
- `duplicate_count`
- `output_uri`

### 7.4 `embedding.runtime.completed`

触发方：

- `embedding-runtime`

触发时机：

- 一个分片或批次推理完成后

`data`字段建议：

- `task_id`
- `shard_id`
- `model`
- `batch_size`
- `vector_dimension`
- `output_uri`
- `latency_ms`

### 7.5 `embedding.vector.upserted`

触发方：

- `vector-store-proxy`

触发时机：

- 向量成功写入向量库后

`data`字段建议：

- `task_id`
- `shard_id`
- `index_id`
- `collection`
- `upsert_count`

### 7.6 `embedding.task.succeeded`

触发方：

- `task-orchestrator`

触发时机：

- 所有分片完成且状态汇总为成功

`data`字段建议：

- `task_id`
- `total_shards`
- `succeeded_shards`
- `failed_shards`
- `result_location`

### 7.7 `embedding.task.failed`

触发方：

- `task-orchestrator`

触发时机：

- 任务进入失败终态

`data`字段建议：

- `task_id`
- `failed_stage`
- `error_code`
- `error_message`
- `retryable`

## 8. 幂等要求

- 同一个 `event_id` 只能被消费一次
- 同一个 `idempotency_key` 的重复事件不得导致重复写入
- 向量写入和任务状态更新必须具备幂等能力

## 9. 审计与可观测要求

- 每个事件必须可追踪到 `tenant_id`、`task_id`、`source`
- 关键终态事件必须入审计日志
- 消费失败必须记录失败原因并支持死信队列

## 10. MVP阶段最低要求

Phase 1 至少落地以下事件：

- `embedding.task.created`
- `embedding.task.queued`
- `embedding.preprocess.completed`
- `embedding.runtime.completed`
- `embedding.vector.upserted`
- `embedding.task.succeeded`
- `embedding.task.failed`
