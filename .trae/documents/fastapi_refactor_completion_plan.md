# 完善 FastAPI 后端与前端功能统一计划 (修正版)

根据用户反馈（移除情感分析，统一改动到文档），本计划旨在完善后端数据接口，优化统计逻辑，并实现关注列表的持久化存储，以达成“清晰明了地看到数据、分析结果和分析进度”的目标。

## 目标
1.  **数据完整性**：完善后端统计接口，将情感分析统计替换为**评分分布统计**，修复趋势图表。
2.  **功能统一**：实现 `Watchlist`（关注列表）的后端存储与前端对接，不再使用 Mock 数据。
3.  **文档更新**：将 API 变更和功能说明同步更新到项目文档中。

## 任务列表

### 1. 后端完善 (server_py)
- [ ] **数据库升级 (database.py)**
    - 修改 `init_db`，创建 `watchlist` 表 (keyword TEXT PRIMARY KEY, created_at TEXT)。
    - 实现 `get_watchlist()` 和 `update_watchlist(keywords)` 函数。
    - 修改 `get_stats` 函数，移除情感统计逻辑，改为统计 **评分分布**：
        - `high_score` (>= 7)
        - `medium_score` (4-6)
        - `low_score` (<= 3)
        - `unrated` (无评分)
- [ ] **API 接口更新 (main.py)**
    - 更新 `GET /api/watchlist` 接口，调用真实的 `get_watchlist`。
    - 更新 `POST /api/watchlist` 接口，调用真实的 `update_watchlist`。
    - 确保 `GET /api/stats` 返回新的评分分布字段。

### 2. 前端对接 (client)
- [ ] **关注配置页面 (Watchlist.jsx)**
    - 移除硬编码的 Mock 数据。
    - 使用 `useEffect` 调用 `getWatchlist` 获取真实关注词。
    - 实现添加/删除关注词时调用 `updateWatchlist` API。
- [ ] **趋势分析页面 (Trends.jsx)**
    - 修改饼图数据源，将“情感倾向分布”改为“评分分布”。
    - 使用后端返回的 `high_score`, `medium_score`, `low_score` 渲染饼图。
    - 确保进度条 (Progress) 能正确显示分析进度。

### 3. 文档更新
- [ ] **更新设计文档 (设计.md 或 README.md)**
    - 记录新增的 `/api/watchlist` 接口定义。
    - 说明统计接口 `/api/stats` 的返回结构变更。
    - 简述前后端交互流程。

## 执行策略
- 先修改后端核心逻辑，确保数据源头正确。
- 再修改前端页面，对接真实数据。
- 最后更新文档。
