# MVP工程骨架说明

## 1. 目标

本文件说明当前仓库已经初始化的 MVP 工程骨架，以及它与前期架构文档之间的对应关系。

当前骨架目标不是一次性实现完整工业级平台，而是先交付：

- 可运行的服务目录和工程模板
- 统一的本地启动方式
- 可复用的共享错误处理、鉴权和日志能力
- 五个关键服务的首版接口骨架

## 2. 当前已初始化的服务

### `gateway`

位置：

- [services/gateway/src/embedding_gateway/app.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/gateway/src/embedding_gateway/app.py)

已具备能力：

- `GET /healthz`
- `GET /readyz`
- `POST /v1/embeddings`
- `POST /v1/tasks/embedding`
- `GET /v1/tasks/{task_id}`
- 基础 `X-API-Key` 校验
- 请求 ID 透传和下游转发

当前说明：

- 该服务目前作为轻量网关实现
- 检索和限流仍是后续阶段补齐项

### `task-orchestrator`

位置：

- [services/control-plane/task-orchestrator/src/embedding_task_orchestrator/app.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/control-plane/task-orchestrator/src/embedding_task_orchestrator/app.py)

已具备能力：

- `POST /internal/tasks/embedding`
- `GET /internal/tasks/{task_id}`
- `GET /internal/queue/stats`
- 内存态任务存储
- 内存态任务队列
- 后台 worker 消费骨架
- 基础重试和死信骨架
- 仓储接口与持久化模型定义
- PostgreSQL 建表 SQL 与 repository 占位实现
- 对 `source.type=inline` 的真实任务执行
- 调用 `preprocess` 生成 chunk
- 调用 `embedding-runtime` 批量生成向量
- 调用 `vector-store-proxy` 批量写入向量
- 结构化事件日志输出

当前说明：

- 当前版本使用内存存储和内存队列 worker
- 任务记录已经抽象出仓储边界和持久化模型
- 后续阶段会替换为 PostgreSQL + Kafka 或等价组件

### `embedding-runtime`

位置：

- [services/data-plane/embedding-runtime/src/embedding_runtime_service/app.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/data-plane/embedding-runtime/src/embedding_runtime_service/app.py)

已具备能力：

- `POST /internal/embeddings`
- 文本输入校验
- 维度校验
- 可重复的伪向量生成逻辑
- 推理事件日志输出

当前说明：

- 当前未接入真实模型框架
- 使用稳定伪向量生成器做占位，便于联调和契约验证
- 后续可替换为 vLLM、Triton、SentenceTransformers 或第三方 API 适配器

### `preprocess`

位置：

- [services/data-plane/preprocess/src/embedding_preprocess_service/app.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/data-plane/preprocess/src/embedding_preprocess_service/app.py)

已具备能力：

- `POST /internal/preprocess/text`
- 文本清洗
- 固定窗口切块
- 重叠窗口配置

当前说明：

- 当前先提供文本切块这一个核心能力
- 去重、脱敏、语言识别和多模态预处理仍是后续阶段能力

### `vector-store-proxy`

位置：

- [services/data-plane/vector-store-proxy/src/embedding_vector_store_proxy/app.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/data-plane/vector-store-proxy/src/embedding_vector_store_proxy/app.py)

已具备能力：

- `POST /internal/vectors/upsert`
- `POST /internal/search`
- 内存态向量索引
- metadata 精确过滤
- 余弦相似度排序

当前说明：

- 当前使用内存结构固化接口和数据模型
- 后续可替换为 Milvus、Qdrant、pgvector 或 OpenSearch

### `retrieval`

位置：

- [services/data-plane/retrieval/src/embedding_retrieval_service/app.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/services/data-plane/retrieval/src/embedding_retrieval_service/app.py)

已具备能力：

- `POST /internal/retrieval/search`
- query 自动转向量
- 调用向量代理服务搜索
- 返回标准检索结果结构

当前说明：

- 当前先做文本 query -> vector -> search 的最小链路
- 重排、混合检索和复杂过滤仍是后续阶段能力

## 3. 共享工程能力

共享能力位置：

- [packages/common/src/embedding_platform_common/errors.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/packages/common/src/embedding_platform_common/errors.py)
- [packages/common/src/embedding_platform_common/auth.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/packages/common/src/embedding_platform_common/auth.py)
- [packages/common/src/embedding_platform_common/observability.py](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/packages/common/src/embedding_platform_common/observability.py)

当前已具备：

- 标准错误响应结构
- API Key 校验辅助方法
- 请求 ID 生成
- 结构化日志辅助函数

## 4. 本地启动方式

### 方式一：使用 Makefile

```bash
make run-embedding-runtime
make run-preprocess
make run-task-orchestrator
make run-vector-store-proxy
make run-retrieval
make run-gateway
```

### 方式二：使用本地脚本

```bash
./scripts/local/run_embedding_runtime.sh
./scripts/local/run_preprocess.sh
./scripts/local/run_task_orchestrator.sh
./scripts/local/run_vector_store_proxy.sh
./scripts/local/run_retrieval.sh
./scripts/local/run_gateway.sh
```

### 方式三：直接使用 uvicorn

需要先配置 `PYTHONPATH`，然后启动对应模块。

## 5. MVP联调示例

### 创建同步Embedding

```bash
curl -X POST http://127.0.0.1:8080/v1/embeddings \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: local-dev-key' \
  -d '{
    "tenant_id": "tenant-a",
    "model": "bge-m3",
    "modality": "text",
    "input": ["hello embedding platform"],
    "dimension": 8
  }'
```

### 创建异步任务

```bash
curl -X POST http://127.0.0.1:8080/v1/tasks/embedding \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: local-dev-key' \
  -d '{
    "tenant_id": "tenant-a",
    "model": "bge-m3",
    "source": {
      "type": "inline",
      "index_id": "demo-index",
      "preprocess": {
        "chunk_size_words": 16,
        "overlap_words": 4
      },
      "items": [
        {"id": "doc-1", "text": "hello embedding platform", "metadata": {"scene": "rag"}},
        {"id": "doc-2", "text": "batch ingestion pipeline", "metadata": {"scene": "rag"}}
      ]
    }
  }'
```

### 写入向量并执行检索

先向 `vector-store-proxy` 写入一条向量：

```bash
curl -X POST http://127.0.0.1:8083/internal/vectors/upsert \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant_id": "tenant-a",
    "index_id": "demo-index",
    "items": [
      {
        "id": "doc-1",
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.1, 0.2, 0.3, 0.4],
        "metadata": {"scene": "rag"}
      }
    ]
  }'
```

再通过网关发起检索：

```bash
curl -X POST http://127.0.0.1:8080/v1/retrieval/search \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: local-dev-key' \
  -d '{
    "tenant_id": "tenant-a",
    "index_id": "demo-index",
    "query": "hello embedding platform",
    "top_k": 3
  }'
```

## 6. 当前未实现项

以下能力仍处于骨架或待接入阶段：

- 真实模型接入
- Redis 缓存
- Kafka 任务投递
- PostgreSQL 任务存储
- 真实向量库接入
- 多租户权限模型
- 限流熔断
- 生产部署清单
- 真正的外部消息队列

## 7. 推荐下一步

1. 将 `task-orchestrator` 从内存存储替换为 PostgreSQL
2. 将 `embedding-runtime` 接入真实文本Embedding模型
3. 为五个服务补充 Dockerfile、健康探针和基础 Kubernetes 部署清单
4. 将内存队列替换为 Kafka / Redis Stream 等正式队列

完成以上步骤后，MVP 将从“可运行骨架”进入“可联调闭环”的下一阶段。
