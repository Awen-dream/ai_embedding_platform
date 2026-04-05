# vector-store-proxy

向量存储代理层，统一封装 Milvus、Qdrant、pgvector、OpenSearch 等后端能力。

## 当前骨架能力

- `POST /internal/vectors/upsert`
- `POST /internal/search`
- SQLite 持久化索引与相似度搜索
- 维度校验和 metadata 过滤

## 本地运行

```bash
make run-vector-store-proxy
```
