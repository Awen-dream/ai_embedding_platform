# 仓库目录规范

## 目标

目录设计遵循行业常见平台型monorepo规范，核心思路是“按职责分层、按边界分目录、按环境分配置、按契约做集成”。

## 顶层目录约定

- `docs/`: 设计文档、契约文档、运维文档、安全规范
- `services/`: 独立可部署微服务
- `packages/`: 共享契约和轻量公共库
- `deploy/`: 部署资产
- `configs/`: 环境配置模板
- `scripts/`: 自动化脚本
- `tests/`: 跨服务测试

## services 规范

`services/`下只放“可独立部署”的服务，每个服务目录建议统一包含：

- `README.md`: 服务职责、依赖、接口、运行方式
- `cmd/`: 启动入口
- `internal/`: 服务私有实现
- `api/`: 服务专属接口定义
- `configs/`: 服务本地配置模板
- `deploy/`: 服务级部署清单
- `tests/`: 服务级测试

在当前蓝图阶段先只创建到服务根目录，后续按服务模板继续展开。

## packages 规范

- `packages/proto`: gRPC、事件Schema、IDL
- `packages/sdk`: 平台SDK
- `packages/common`: 认证、日志、配置、错误码、追踪等公共能力

约束：

- `packages/common`只放真正跨服务复用的稳定能力
- 不允许业务逻辑下沉到`common`
- 接口契约优先放`proto`或`docs/api`

## deploy 规范

- `deploy/kubernetes/base`: 基础资源模板
- `deploy/kubernetes/overlays/*`: 环境差异配置
- `deploy/helm`: 对外或内部标准Chart
- `deploy/terraform`: 云资源编排

## configs 规范

- `configs/dev`
- `configs/stage`
- `configs/prod`

仅保存模板与示例，不提交密钥、证书和生产敏感配置。

## tests 规范

- `tests/contract`: 接口契约与兼容性测试
- `tests/integration`: 跨服务集成测试
- `tests/performance`: 性能、压测、容量验证

## 命名规范

- 目录名优先使用小写加中划线，如`embedding-runtime`
- API版本使用显式版本号，如`/v1/embeddings`
- Kafka Topic、事件名、错误码建议统一前缀，如`embedding.task.created`

## 变更原则

- 新增服务必须说明职责边界，避免与已有服务重叠
- 新增共享库必须证明其跨服务复用价值
- 目录调整优先通过文档和ADR说明原因
