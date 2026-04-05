# 错误码规范

## 1. 目标

统一平台错误码体系，保证以下目标：

- 对业务方暴露稳定、可预测的错误语义
- 对平台内部提供一致的日志归因和告警标签
- 支持跨服务问题排查，而不是每个服务定义一套错误风格

错误码遵循：

- 机器可读
- 人类可理解
- 可按服务和错误类别路由告警
- 与HTTP状态码解耦但可映射

## 2. 错误响应结构

建议所有对外API统一返回以下结构：

```json
{
  "request_id": "req_123",
  "error": {
    "code": "EMB-VAL-400001",
    "message": "input is required",
    "type": "validation_error",
    "retryable": false,
    "details": {
      "field": "input"
    }
  }
}
```

字段说明：

- `request_id`: 用于排查日志和链路追踪
- `code`: 平台标准错误码
- `message`: 面向调用方的简洁提示，不暴露内部敏感信息
- `type`: 错误大类
- `retryable`: 调用方是否建议重试
- `details`: 可选结构化附加字段

## 3. 错误码编码规则

统一格式：

`<DOMAIN>-<CATEGORY>-<NUMBER>`

示例：

- `EMB-VAL-400001`
- `AUTH-PERM-403001`
- `TASK-STATE-409001`

### 3.1 DOMAIN

- `EMB`: Embedding相关
- `AUTH`: 鉴权和权限
- `TASK`: 异步任务
- `VEC`: 向量存储
- `RET`: 检索服务
- `MODEL`: 模型路由与模型运行
- `SYS`: 系统级错误

### 3.2 CATEGORY

- `VAL`: 参数校验
- `AUTHN`: 身份认证
- `PERM`: 权限不足
- `STATE`: 状态冲突
- `LIMIT`: 限流或配额
- `DEP`: 下游依赖异常
- `TIMEOUT`: 超时
- `NOTFOUND`: 资源不存在
- `INTERNAL`: 内部错误

### 3.3 NUMBER

建议按HTTP语义分段：

- `400xxx`: 请求非法
- `401xxx`: 未认证
- `403xxx`: 权限不足
- `404xxx`: 资源不存在
- `409xxx`: 状态冲突
- `429xxx`: 限流/配额
- `500xxx`: 平台内部错误
- `502xxx`: 下游依赖失败
- `504xxx`: 超时

## 4. 错误类型定义

| type | 含义 | 是否建议重试 |
|---|---|---|
| `validation_error` | 参数或输入格式错误 | 否 |
| `authentication_error` | 未认证或凭证非法 | 否 |
| `authorization_error` | 已认证但无权限 | 否 |
| `not_found_error` | 请求资源不存在 | 否 |
| `conflict_error` | 状态冲突或重复请求 | 否 |
| `rate_limit_error` | 限流或配额不足 | 是，按策略重试 |
| `dependency_error` | 下游依赖失败 | 是 |
| `timeout_error` | 超时 | 是 |
| `internal_error` | 平台内部异常 | 视情况 |

## 5. 首批标准错误码

### 5.1 通用与系统类

| 错误码 | HTTP | type | 含义 | retryable |
|---|---|---|---|---|
| `SYS-INTERNAL-500001` | 500 | `internal_error` | 未知内部错误 | 否 |
| `SYS-TIMEOUT-504001` | 504 | `timeout_error` | 请求处理超时 | 是 |
| `SYS-DEP-502001` | 502 | `dependency_error` | 下游服务不可用 | 是 |
| `SYS-LIMIT-429001` | 429 | `rate_limit_error` | 平台整体限流 | 是 |

### 5.2 鉴权类

| 错误码 | HTTP | type | 含义 | retryable |
|---|---|---|---|---|
| `AUTH-AUTHN-401001` | 401 | `authentication_error` | 缺少认证信息 | 否 |
| `AUTH-AUTHN-401002` | 401 | `authentication_error` | API Key无效 | 否 |
| `AUTH-PERM-403001` | 403 | `authorization_error` | 租户无权访问目标资源 | 否 |
| `AUTH-LIMIT-429001` | 429 | `rate_limit_error` | 租户配额不足 | 是 |

### 5.3 Embedding类

| 错误码 | HTTP | type | 含义 | retryable |
|---|---|---|---|---|
| `EMB-VAL-400001` | 400 | `validation_error` | input不能为空 | 否 |
| `EMB-VAL-400002` | 400 | `validation_error` | model不能为空 | 否 |
| `EMB-VAL-400003` | 400 | `validation_error` | modality非法 | 否 |
| `EMB-VAL-400004` | 400 | `validation_error` | 输入超过长度限制 | 否 |
| `EMB-NOTFOUND-404001` | 404 | `not_found_error` | 模型不存在或不可用 | 否 |
| `EMB-DEP-502001` | 502 | `dependency_error` | 模型提供方调用失败 | 是 |
| `EMB-TIMEOUT-504001` | 504 | `timeout_error` | Embedding生成超时 | 是 |

### 5.4 任务类

| 错误码 | HTTP | type | 含义 | retryable |
|---|---|---|---|---|
| `TASK-VAL-400001` | 400 | `validation_error` | 任务请求参数非法 | 否 |
| `TASK-NOTFOUND-404001` | 404 | `not_found_error` | task_id不存在 | 否 |
| `TASK-STATE-409001` | 409 | `conflict_error` | 当前任务状态不允许该操作 | 否 |
| `TASK-STATE-409002` | 409 | `conflict_error` | 重复提交幂等任务 | 否 |
| `TASK-DEP-502001` | 502 | `dependency_error` | 任务投递队列失败 | 是 |

### 5.5 向量与检索类

| 错误码 | HTTP | type | 含义 | retryable |
|---|---|---|---|---|
| `VEC-VAL-400001` | 400 | `validation_error` | 向量维度不匹配 | 否 |
| `VEC-NOTFOUND-404001` | 404 | `not_found_error` | index或collection不存在 | 否 |
| `VEC-DEP-502001` | 502 | `dependency_error` | 向量库调用失败 | 是 |
| `RET-VAL-400001` | 400 | `validation_error` | top_k非法 | 否 |
| `RET-VAL-400002` | 400 | `validation_error` | query和vector不能同时为空 | 否 |

## 6. HTTP状态码映射

| HTTP状态码 | 适用场景 |
|---|---|
| `400` | 参数错误、请求格式错误 |
| `401` | 认证失败 |
| `403` | 权限不足、租户越权 |
| `404` | 模型、任务、索引不存在 |
| `409` | 状态冲突、幂等冲突 |
| `429` | 限流、配额不足 |
| `500` | 平台内部未分类错误 |
| `502` | 下游依赖失败 |
| `504` | 超时 |

## 7. 使用要求

- 对外接口必须返回标准错误结构
- 日志中必须记录 `request_id`、`error.code`、`tenant_id`
- 监控指标必须支持按 `error.code` 和 `error.type` 聚合
- 不允许直接把下游原始报错透传给业务方

## 8. MVP阶段建议

Phase 1 至少实现以下错误码：

- 认证类：`AUTH-AUTHN-401001`、`AUTH-AUTHN-401002`
- Embedding类：`EMB-VAL-400001`、`EMB-VAL-400002`、`EMB-TIMEOUT-504001`
- 任务类：`TASK-NOTFOUND-404001`、`TASK-STATE-409001`
- 检索类：`RET-VAL-400001`
- 系统类：`SYS-INTERNAL-500001`
