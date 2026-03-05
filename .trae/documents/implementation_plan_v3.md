# 实施计划：数据资产时间维度筛选与交互增强

本计划旨在增强“数据资产概览”页面的交互性，支持按时间范围（默认一天、一周、一月）筛选数据，并提供热门标签点击查看相关新闻的功能。

## 1. 后端 API 增强 (Python/FastAPI)

### 1.1 修改 `server_py/services/news_service.py`
- [ ] 更新 `get_tag_stats`、`get_type_stats`、`get_top_entities` 方法，增加 `start_date` 和 `end_date` 参数。
- [ ] 在 SQL 查询中增加时间范围过滤条件 (`WHERE created_at BETWEEN ? AND ?`)。
- [ ] 确保 `get_news` 方法已支持 `tag` 筛选（之前已规划，需确认实现）。

### 1.2 修改 `server_py/routers/news.py`
- [ ] 更新统计相关的 API 端点，接收 `start_date` 和 `end_date` 查询参数。

## 2. 前端页面开发 (React)

### 2.1 日期筛选器 (`client/src/pages/DataExplorer.jsx`)
- [ ] 在页面顶部添加 Ant Design 的 `Radio.Group`（一天 / 一周 / 一月）和 `DatePicker.RangePicker`。
- [ ] 默认选中“一周”（最近7天）。
- [ ] 当日期变化时，重新触发所有统计数据的 `fetchData`。

### 2.2 标签云交互优化 (`client/src/pages/DataExplorer.jsx`)
- [ ] **默认展示与展开**：
    - 增加 `showAllTags` 状态，默认只渲染 Top 20 标签。
    - 添加“查看更多 / 收起”按钮（Button type="link"）。
- [ ] **点击查看新闻弹框 (Modal)**：
    - 当用户点击某个 `Tag` 时，打开一个 `Modal`。
    - `Modal` 内嵌 `NewsList` 组件（复用或新建），传入选中的 `tag` 和当前的 `dateRange` 作为筛选条件。
    - 允许用户在弹框内快速浏览该标签下的相关新闻。

### 2.3 API 集成 (`client/src/services/api.js`)
- [ ] 修改 `getTagStats`、`getTypeStats`、`getTopEntities`，支持传递日期参数。
- [ ] 新增 `getNewsByTag(tag, startDate, endDate)` 方法（复用 `getNews`）。

## 3. 验证与交付
- [ ] 启动服务，切换“一天”、“一周”按钮，验证统计图表是否即时刷新。
- [ ] 点击热门标签（如“黄金”），验证弹框是否弹出并正确显示该标签下的新闻列表。
