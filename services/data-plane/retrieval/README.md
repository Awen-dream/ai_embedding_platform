# retrieval

检索服务，负责 ANN 召回、过滤、混合检索、重排与结果组装。

## 当前骨架能力

- `POST /internal/retrieval/search`
- query 转向量
- 调用向量代理服务搜索
- 结果标准化返回

## 本地运行

```bash
make run-retrieval
```
