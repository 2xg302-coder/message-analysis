# 后端 Python 迁移与改进计划

鉴于引入 AkShare 进行数据采集的需求，以及未来在数据分析和 AI 处理上的扩展性，**非常有必要**将后端从 Node.js 迁移至 Python。这将消除“双语言”维护成本，并能直接利用 Python 强大的数据和 AI 生态。

本计划将原定的“修补式”改进升级为“重构式”改进，使用 **FastAPI** 重写后端。

## 1. 技术栈选型

* **Web 框架**: FastAPI (高性能，原生支持异步，自动生成文档)

* **数据库**: SQLite (沿用现有 `news.db` 文件，无缝切换)

* **数据采集**: AkShare (原生 Python 库)

* **AI 交互**: OpenAI Python SDK (兼容 DeepSeek)

* **定时任务**: APScheduler (替代简单的 `setInterval` 和 Cron)

* **HTTP 服务**: Uvicorn

## 2. 迁移与功能实现步骤

我们将新建 `server_py` 目录进行开发，确保不破坏原有 `server`，待验证通过后再替换。

### 2.1 环境初始化

* **目录**: 创建 `server_py/`

* **依赖**: `requirements.txt` (包含 `fastapi`, `uvicorn`, `sqlite3`, `akshare`, `openai`, `apscheduler`, `pydantic`)

### 2.2 数据库层 (Database Layer)

* **文件**: `server_py/database.py`

* **功能**:

  * 连接现有的 `news.db`。

  * 实现 `get_latest_news`, `add_news`, `get_stats`, `get_series_list` 等原有方法。

  * **改进**: 使用 Pydantic 模型定义数据结构，提高类型安全。

### 2.3 核心业务逻辑 (Core Services)

* **LLM 服务 (`server_py/llm_service.py`)**:

  * **迁移**: 移植 `analyzeNews` 逻辑。

  * **改进**: 实现 Prompt 优化，接受 `existing_tags` 参数，引导连续剧一致性。

* **采集服务 (`server_py/collector.py`)**:

  * **新增**: 集成 AkShare，直接调用 API 获取新闻。

  * **功能**: 数据清洗、去重、入库。

* **分析服务 (`server_py/analyzer.py`)**:

  * **迁移**: 移植 Worker 轮询逻辑。

  * **改进**:

    * 获取 `existing_tags` 传入 LLM。

    * 增加 `tenacity` 库实现指数退避重试 (Retry)。

### 2.4 API 接口层 (API Layer)

* **文件**: `server_py/main.py`

* **功能**:

  * 复刻 Node.js 的所有路由 (`/api/news`, `/api/stats`, `/api/series` 等)。

  * 确保返回的 JSON 结构与原版完全一致，**前端无需任何修改**。

  * 集成 `APScheduler`，在应用启动时自动开启“采集”和“分析”定时任务。

## 3. 验证与切换

1. **启动 Python 后端**: 使用 `uvicorn` 在新端口 (或原端口 3001) 启动。
2. **API 测试**: 验证前端页面能否正常加载数据、显示统计。
3. **功能验证**:

   * 确认 AkShare 能够自动抓取数据入库。

   * 确认 LLM 分析任务正常运行且能复用标签。
4. **切换**: 确认无误后，更新项目启动脚本，将后端指向 Python 版本。

## 4. 文件结构预览

```
server_py/
├── main.py            # 入口 & API 路由
├── database.py        # 数据库操作
├── config.py          # 环境变量配置
├── services/
│   ├── llm_service.py # AI 分析
│   ├── collector.py   # AkShare 采集
│   └── analyzer.py    # 分析任务调度
├── requirements.txt
└── .env               # 配置
```

