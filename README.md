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
- API契约草案：[docs/api/openapi/embedding-platform.openapi.yaml](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/api/openapi/embedding-platform.openapi.yaml)

## 当前阶段

当前仓库已完成：

- 平台总体架构设计
- 工业级能力基线定义
- 标准化目录骨架初始化
- OpenAPI初始契约草案

后续建议优先落地：

1. 定义错误码、鉴权模型、租户模型与事件模型
2. 初始化`gateway`、`embedding-runtime`、`task-orchestrator`三个MVP服务
3. 增加本地开发环境与Kubernetes基础部署清单
