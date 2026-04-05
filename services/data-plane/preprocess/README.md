# preprocess

数据预处理服务，负责清洗、切块、去重、脱敏和多模态标准化。

## 当前骨架能力

- `POST /internal/preprocess/text`
- 文本清洗
- 固定窗口切块
- 重叠窗口配置

## 本地运行

```bash
make run-preprocess
```
