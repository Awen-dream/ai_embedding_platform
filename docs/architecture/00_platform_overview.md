# 平台总览

## 定位

AI Embedding Platform 是一个面向企业内部多业务线复用的向量化基础设施平台，负责统一承接数据输入、预处理、Embedding生成、向量存储、检索服务、可观测与成本治理。

## 平台边界

本平台负责：

- 标准化Embedding与检索API
- 模型路由、推理治理、异步批处理
- 向量索引生命周期管理
- 多租户、权限、审计、成本、SLO治理

本平台不直接负责：

- 具体业务应用页面
- LLM问答编排
- 业务侧知识加工规则

这些能力通过SDK、API或事件与平台集成。

## 设计原则

- API First：先定义REST/gRPC/事件契约
- Stateless First：控制面尽量无状态，状态沉淀到标准存储
- Multi-tenant by Default：所有核心对象都具备租户边界
- Observability Built-in：日志、指标、追踪、审计为默认能力
- Security by Design：鉴权、脱敏、加密、审计在设计期内建
- Progressive Delivery：支持灰度、回滚、双写、旁路验证

## 建议技术路线

- 控制面优先使用Go或Java，适合高并发服务治理
- 推理和预处理可结合Python生态与GPU推理框架
- 接口层统一OpenAPI + gRPC
- 部署统一以Kubernetes为目标形态

## 与总体设计关系

本文件用于提供平台化视角的总览，详细的六层架构说明见：

- [docs/embedding_platform_architecture.md](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/docs/embedding_platform_architecture.md)
