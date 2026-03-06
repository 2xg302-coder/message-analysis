# 模块 A: 每日主线生成与 LLM 服务 (Daily Storyline Generation) - [已完成]

## 1. 目标
利用大模型（LLM）基于每日财经日历数据，自动提取当日核心市场主线（Storylines）。该模块独立负责与 LLM 的交互及原始日历数据的解析。

## 2. 独立性说明
- **输入**：`calendar_events` 表中的日历数据（JSON/Dict 列表）。
- **输出**：结构化的主线事件列表（JSON）。
- **依赖**：仅依赖 `openai` 或兼容的 LLM 客户端库，不依赖其他业务逻辑。

## 3. 实现步骤

### 3.1 LLM 服务封装 (`server_py/services/llm_service.py`) [x]
- 创建 `LLMService` 类，封装 OpenAI 兼容接口。
- 支持配置：`API_KEY`, `BASE_URL`, `MODEL_NAME`。
- 提供 `chat_completion(prompt, system_prompt)` 方法。
- 实现重试机制（Retrying）以应对 API 不稳定。

### 3.2 Prompt 工程 (`server_py/prompts/storyline_prompt.py`) [x]
- 设计 System Prompt：
    > "你是一个专业的金融分析师。你的任务是从一天的财经日历中，识别出最可能影响市场的 3-5 个核心主线事件。忽略次要数据。"
- 设计 User Prompt 模板：
    > "这是今天的财经日历数据：{calendar_data}。请输出 JSON 格式的主线列表，包含：title, keywords (list), description, importance (1-5), expected_impact."
- 增加 Output Parser，确保 LLM 返回合法的 JSON 格式。

### 3.3 主线生成逻辑 (`server_py/services/storyline_generator.py`) [x]
- 实现 `generate_daily_storylines(date)` 函数。
- 逻辑：
    1. 从数据库读取指定日期的 `calendar_events`（重要性 >= 2）。
    2. 格式化为 Prompt 字符串。
    3. 调用 `LLMService`。
    4. 解析返回的 JSON。
    5. 返回 Storyline 对象列表。

## 4. 测试计划 [x]
- 编写单元测试 `tests/test_llm_service.py`，mock LLM 响应。
- 编写集成测试，使用真实的日历数据调用 LLM，验证输出格式。
