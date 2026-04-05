# gateway

统一入口服务，负责鉴权、路由转发、版本管理和观测上下文注入。

## 当前骨架能力

- `GET /healthz`
- `GET /readyz`
- `POST /v1/embeddings`
- `POST /v1/tasks/embedding`
- `GET /v1/tasks/{task_id}`
- 配置化租户凭证校验
- 每租户限流
- 轻量下游熔断保护

## 本地运行

```bash
make run-gateway
```
