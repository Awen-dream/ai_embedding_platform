# AI Embedding Platform

工业级Embedding平台蓝图与标准化仓库骨架。

## 目标

本仓库用于承载企业级Embedding平台的设计、接口契约、服务实现、部署配置与运维规范，强调以下原则：

- 平台化：多租户、多模型、多模态、跨业务复用
- 工业级：高可用、可观测、可审计、可治理、可扩展
- 契约优先：先定义API、事件、数据模型，再推进服务实现
- 目录标准化：采用行业通用monorepo组织方式，降低协作和运维成本

## 仓库结构

```text
.
├── configs/                 # 环境配置模板(dev/stage/prod)
├── deploy/                  # Kubernetes/Helm/Terraform 部署资产
├── docs/                    # 架构、接口、运行手册、安全规范
├── packages/                # 跨服务共享契约与公共库
├── scripts/                 # 本地开发、发布、校验脚本
├── services/                # 平台微服务实现
└── tests/                   # 合约、集成、性能测试
```

## 服务分层

- `services/gateway`: 网关与统一入口
- `services/control-plane`: 租户、模型、任务、索引、成本等控制面
- `services/data-plane`: 接入、预处理、推理、缓存、检索、向量代理等数据面
- `packages/proto`: gRPC/事件契约
- `packages/sdk`: 对内对外SDK
- `packages/common`: 认证、日志、追踪、配置、错误码等公共能力

## 文档入口

- 总体设计：[docs/embedding_platform_architecture.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/embedding_platform_architecture.md)
- 平台总览：[docs/architecture/00_platform_overview.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/00_platform_overview.md)
- 工业级能力基线：[docs/architecture/01_industrial_capability_baseline.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/01_industrial_capability_baseline.md)
- 仓库规范：[docs/architecture/02_repository_layout.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/02_repository_layout.md)
- 服务边界：[docs/architecture/03_service_boundaries.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/03_service_boundaries.md)
- 实施路线图：[docs/architecture/04_implementation_roadmap.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/04_implementation_roadmap.md)
- Phase 0-1 交付计划：[docs/architecture/05_phase0_phase1_delivery_plan.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/05_phase0_phase1_delivery_plan.md)
- 任务状态机：[docs/architecture/06_task_state_machine.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/06_task_state_machine.md)
- API契约草案：[docs/api/openapi/embedding-platform.openapi.yaml](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/api/openapi/embedding-platform.openapi.yaml)
- 错误码规范：[docs/api/error_codes.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/api/error_codes.md)
- 事件模型规范：[docs/api/event_model.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/api/event_model.md)
- MVP工程骨架：[docs/architecture/07_mvp_scaffold.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/architecture/07_mvp_scaffold.md)

## 当前阶段

当前仓库已完成：

- 平台总体架构设计
- 工业级能力基线定义
- 标准化目录骨架初始化
- OpenAPI初始契约草案
- `gateway`、`task-orchestrator`、`embedding-runtime`、`preprocess`、`vector-store-proxy`、`retrieval` 六个 MVP 服务骨架
- 统一的 Python monorepo 启动配置、共享错误处理和本地运行脚本

## 本地启动

先安装依赖：

```bash
pip install -e .
```

然后分别启动：

```bash
make run-embedding-runtime
make run-preprocess
make run-task-orchestrator
make run-vector-store-proxy
make run-retrieval
make run-gateway
```

## 后续建议优先落地

1. 接入真实Embedding模型并替换伪向量生成器
2. 将 `task-orchestrator` 的内存队列替换为 Kafka / Redis Stream，并引入持久化任务表
3. 为 `preprocess` 补去重、脱敏和更丰富的切块策略
4. 增加 Dockerfile 和 Kubernetes 基础部署清单
