# common

存放最小化共享公共能力，如日志、配置、追踪、错误码与鉴权中间件。

## 当前已实现

- `src/embedding_platform_common/errors.py`: 标准错误结构与异常对象
- `src/embedding_platform_common/auth.py`: API Key 校验辅助方法
- `src/embedding_platform_common/ids.py`: 请求 ID 生成
- `src/embedding_platform_common/observability.py`: 结构化日志辅助方法
