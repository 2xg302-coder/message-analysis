# 系统全面升级实施计划 (Execution Plan)

**确认：** 我们可以将任务拆分为 4 个模块。作为 AI 助手，我将按照逻辑依赖顺序（A -> B -> C -> D）依次为您编写和重构代码，确保所有模块无缝集成。

## 1. 模块 A：基础设施重构 (立即执行)
**目标**：建立纯 Python 后端，定义数据标准。
- [x] **清理**：移除 `server/` (Node.js)，清理 `package.json`。
- [x] **Schema**：重写 `server_py/database.py`，添加 `type`, `tags`, `impact_score` 等字段。
- [x] **API**：更新 `server_py/main.py`，配置 FastAPI 路由和 Pydantic 模型。

## 2. 模块 B：采集与预处理 (紧随其后)
**目标**：接入新浪快讯，实现去重和清洗。
- [x] **采集器**：创建 `server_py/collectors/sina.py` (快讯) 和 `eastmoney.py` (深度)。
- [x] **预处理**：创建 `server_py/processor.py`，实现 SimHash 去重、正则清洗和 FlashText 实体识别。
- [x] **调度**：在 `main.py` 中集成 `apscheduler` 调度采集任务。

## 3. 模块 C：深度分析引擎 (第三步)
**目标**：增强 LLM 分析能力。
- [x] **Prompt**：在 `server_py/llm_service.py` 中更新 Prompt，要求 JSON 格式输出（含评分、情感）。
- [x] **分析器**：更新 `server_py/analyzer.py`，解析 LLM 返回的 JSON 并存入数据库。

## 4. 模块 D：前端适配 (最后一步)
**目标**：前端展示新数据。
- [x] **API 客户端**：修改 `client/src/services/api.js` 指向 Python 端口。
- [x] **UI 组件**：
    - 更新 `NewsFeed.jsx` 支持快讯/深度双视图。
    - 更新 `Sidebar.jsx` 增加高级筛选。
    - 更新 `Trends.jsx` 展示情感热力图。

## 5. 性能优化 (本次更新)
**目标**：解决 API 响应延迟问题。
- [x] **异步 LLM 调用**：
    - **问题**：`llm_service.py` 使用同步 `OpenAI` 客户端，导致 LLM 分析时阻塞主线程（Event Loop），所有 API 请求（如 `/api/news`）被卡住约 2 秒。
    - **解决**：迁移至 `AsyncOpenAI` 客户端，将 `call_llm` 改为异步方法，释放 Event Loop。
- [x] **数据库索引**：
    - **优化**：在 `database.py` 中为 `created_at` 和 `impact_score` 添加索引，加速列表过滤查询。

---
**准备就绪**：请批准此计划，我将立即从 **模块 A** 开始执行。
