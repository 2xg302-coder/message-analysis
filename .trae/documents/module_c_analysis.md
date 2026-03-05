# 模块 C：深度分析引擎 (Deep Analysis Engine)

**目标**：提升 LLM 的分析质量，支持多维度评级和情感分析。

## 1. Prompt 优化 (`server_py/prompts.py`)

### 结构化输出
设计新的 Prompt，要求 LLM 输出严格的 JSON 格式：

```json
{
  "summary": "新闻的 30 字摘要",
  "entities": {
    "600519": "贵州茅台",
    "AAPL": "Apple"
  },
  "tags": ["宏观", "白酒", "消费"],
  "impact_score": 5, // 1-5
  "sentiment_score": 0.8, // -1.0 to 1.0
  "event_type": "并购重组" // 枚举值：业绩、并购、政策、宏观、人事、其他
}
```

### Few-shot Learning
在 Prompt 中包含 3-5 个示例（Examples），覆盖：
- 明显的利好（如“净利润增长 200%”）。
- 明显的利空（如“被证监会立案调查”）。
- 中性新闻（如“召开股东大会”）。

## 2. 情感分析策略 (`server_py/analyzer.py`)

### 2.1 基于 LLM 的情感分析
- **逻辑**：将新闻全文作为输入，要求 LLM 评估对提及实体的利好/利空程度。
- **配置**：`server_py/config.py` 中增加 `LLM_MODEL` 配置（推荐 DeepSeek-chat 或 GPT-3.5-turbo）。

### 2.2 本地规则补充 (可选)
- 如果 LLM 调用失败或超时，回退到基于情感词典的简单打分。
- 维护 `positive_words.txt` 和 `negative_words.txt`。

## 3. 异步任务调度
- **工具**：`apscheduler` 或简单的 `asyncio.create_task`。
- **逻辑**：
  - 定期（每 5 分钟）扫描数据库中 `analysis IS NULL` 且 `type='article'` 的记录。
  - 批量发送给 LLM（注意 API 限流）。
  - 更新数据库 `analysis` 字段，同时回填 `impact_score`, `sentiment_score` 等结构化字段。
