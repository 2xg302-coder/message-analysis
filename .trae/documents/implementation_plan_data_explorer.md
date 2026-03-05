# 实施计划：数据资产概览页面 (Data Explorer)

本计划旨在现有的前端项目中新增一个“数据资产概览”页面，用于直观展示系统已积累的数据资产，包括通过模型抽取的标签、实体和事件类型分布。

## 1. 后端 API 增强 (Python/FastAPI)

我们需要新增接口来返回标签、实体和类型的统计数据。

### 1.1 修改 `server_py/services/news_service.py`
- [ ] 实现 `get_tag_stats(limit=100)` 方法：
    - 遍历数据库中的 `analysis` 字段，统计 `tags` 列表中各标签的出现频率。
    - 返回按频率降序排列的标签列表。
- [ ] 实现 `get_type_stats()` 方法：
    - 统计 `analysis` 字段中 `event_type` 的分布情况。

### 1.2 修改 `server_py/routers/news.py`
- [ ] 新增端点 `GET /api/stats/tags`: 返回热门标签及计数。
- [ ] 新增端点 `GET /api/stats/types`: 返回事件类型分布。

## 2. 前端页面开发 (React)

### 2.1 新增页面 `client/src/pages/DataExplorer.jsx`
我们将创建一个全新的页面来展示这些统计信息。
- [ ] **页面布局**：使用 Ant Design 的 `Card` 和 `Row/Col` 布局。
- [ ] **标签云 (Tags Cloud)**：
    - 获取 `/api/stats/tags` 数据。
    - 使用不同大小/颜色的 `Tag` 组件展示，点击可跳转到新闻筛选页（可选）。
- [ ] **实体排行 (Entities Leaderboard)**：
    - 调用现有的 `/api/entities` 接口。
    - 使用 `Table` 组件展示 Top 50 实体（名称、提及次数）。
- [ ] **类型分布 (Event Types)**：
    - 获取 `/api/stats/types` 数据。
    - 使用 Recharts 绘制饼图 (PieChart)，展示“宏观”、“公司”、“地缘政治”等类型的占比。

### 2.2 路由与导航配置
- [ ] 修改 `client/src/App.jsx`：
    - 注册新路由 `/explorer` 指向 `DataExplorer` 组件。
- [ ] 修改 `client/src/layouts/MainLayout.jsx`：
    - 在侧边栏菜单 (`items`) 中添加“数据资产”入口 (图标推荐 `DatabaseOutlined`)。

### 2.3 API 封装
- [ ] 修改 `client/src/services/api.js`：
    - 添加 `getTagsStats` 和 `getTypesStats` 方法。

## 3. 验证
- [ ] 启动前后端服务。
- [ ] 访问“数据资产”页面，确认能看到标签云、实体列表和类型分布图。
- [ ] 确认数据与数据库中的实际内容一致。
