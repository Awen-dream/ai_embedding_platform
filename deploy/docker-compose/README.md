# docker-compose

本目录存放本地开发和联调用的基础设施编排文件。

## 当前文件

- [local-brokers.yml](/Users/liuwenzhong/PycharmProjects/ai_embedding_platform/deploy/docker-compose/local-brokers.yml)

## 当前用途

- 启动本地 `Redis`
- 启动本地单节点 `Kafka`
- 为 `task-orchestrator` 的 `redis_stream` / `kafka` 队列后端提供联调环境

## 建议用法

```bash
make broker-up
make broker-logs
make broker-down
```
