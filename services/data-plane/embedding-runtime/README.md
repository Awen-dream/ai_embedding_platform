# embedding-runtime

Embedding推理运行时，负责同步推理、动态批处理、模型适配和 GPU 调度协同。

## 当前骨架能力

- `POST /internal/embeddings`
- 文本输入校验
- 维度校验
- 可插拔 embedding provider
- `openai-compatible` HTTP provider 适配
- 本地 hashing provider 作为开发回退

## 本地运行

```bash
make run-embedding-runtime
```
