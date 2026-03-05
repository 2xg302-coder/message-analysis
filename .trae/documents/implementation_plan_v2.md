# 实施计划：数据资产概览与小模型快速处理链路

本计划包含两部分核心工作：
1.  **后端优化**：实现基于小模型（Local LLM）的高频、快速新闻分析链路，确保数据能被及时打标和分类。
2.  **前端展示**：新增“数据资产概览”页面，直观展示积累的标签、实体、类型以及系统的处理状态。

## 1. 后端：小模型快速处理链路 (Python/FastAPI)

### 1.1 优化 `server_py/services/llm_service.py`
- [ ] **适配本地模型**：增强 `call_llm` 方法，针对本地模型（如 Ollama/vLLM）进行优化。
    - 增加 `timeout` 设置，防止本地模型卡死。
    - 增加简化的 Prompt 模板（`FAST_ANALYSIS_PROMPT`），减少 Token 消耗，提升处理速度。

### 1.2 重构 `server_py/analyzer.py` (分析调度器)
- [ ] **提高调度频率**：将分析任务的间隔从 5 分钟调整为 **10秒**，实现准实时处理。
- [ ] **并发控制**：引入 `asyncio.Semaphore`，限制并发请求数（默认为 2-4），避免压垮本地小模型显存。
- [ ] **批处理优化**：每次从数据库获取 10-20 条未分析新闻（Pending），批量送入队列处理。

### 1.3 增强 `server_py/processor.py` (预处理)
- [ ] **规则预打标**：在调用 LLM 之前，先利用正则/关键词进行“快速打标”（如识别“快讯”、“公告”、“加息”等显眼词），确保数据入库时即具备基础标签，减轻 LLM 负担。

### 1.4 新增统计 API (`server_py/routers/news.py`)
- [ ] 新增 `GET /api/stats/tags`: 返回热门标签及计数（用于前端词云）。
- [ ] 新增 `GET /api/stats/types`: 返回事件类型分布（用于前端饼图）。
- [ ] 增强 `GET /api/stats`: 返回 `processing_rate`（每分钟处理条数）和 `avg_latency`（平均耗时）。

## 2. 前端：数据资产概览页面 (React)

### 2.1 新增页面 `client/src/pages/DataExplorer.jsx`
- [ ] **系统状态看板**：
    - 展示“待处理队列”长度（Pending News）。
    - 展示“当前处理速度”（如：120条/分钟）。
    - 状态指示灯：🟢 分析服务运行中 | 🔴 已暂停。
- [ ] **数据资产可视化**：
    - **标签云 (Tags Cloud)**：按热度展示“加息”、“黄金”、“战争”等标签。
    - **实体排行 (Entities Leaderboard)**：展示 Top 50 热门实体。
    - **类型分布 (Event Types)**：饼图展示事件类型占比。

### 2.2 路由与导航
- [ ] 在 `client/src/App.jsx` 中注册 `/explorer` 路由。
- [ ] 在 `client/src/layouts/MainLayout.jsx` 侧边栏添加“数据资产”入口。

## 3. 验证与交付
- [ ] **后端验证**：启动服务，模拟写入新闻，观察 `analyzer` 是否在 10秒内自动启动并完成分析（查看日志 `processing_rate`）。
- [ ] **前端验证**：进入“数据资产”页面，确认能看到标签云、实体列表以及实时的处理进度。
