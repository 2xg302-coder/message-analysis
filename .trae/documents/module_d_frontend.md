# 模块 D：前端适配与展示 (Frontend Adaptation)

**目标**：适配新的 Python 后端，提供更直观、更丰富的数据展示。

## 1. API 客户端升级 (`client/src/services/api.js`)

### 1.1 修改 Base URL
将 `localhost:3000` 更改为 `localhost:8000` (假设 Python 服务端口)。

### 1.2 接口适配
- 移除 Node.js 特有的 `/api/data`，替换为 `/api/news`。
- 增加对 `type` (flash/article) 的参数支持。
- 解析新的 JSON 结构 (`tags`, `entities`, `impact_score`, `sentiment_score`)。

## 2. UI 组件升级

### 2.1 新闻列表组件 (`NewsFeed.jsx`)
- **快讯模式**：更紧凑的列表项，仅展示时间、标题、标签。
  - 使用 `react-window` 或 `react-virtualized` 实现长列表滚动优化。
- **深度模式**：保留卡片式设计，增加摘要和情感颜色条。
  - 红色边框：利好 (Score > 0.5)
  - 绿色边框：利空 (Score < -0.5)
  - 黄色边框：重要 (Impact Score >= 4)

### 2.2 侧边栏筛选 (`Sidebar.jsx`)
- **新增筛选器**：
  - **重要度**：Checkbox [★★★★★, ★★★★☆, ...]
  - **情感**：Radio [利好, 利空, 中性]
  - **实体**：Autocomplete 输入框，支持搜索股票代码/名称。

### 2.3 统计图表 (`Trends.jsx`)
- 利用新的 `impact_score` 和 `sentiment_score` 绘制热力图。
- 展示今日最热实体云图 (`WordCloud`)。

## 3. 依赖库
- `axios` (API 请求)
- `recharts` (图表)
- `react-window` (虚拟列表，可选)
- `mui` (组件库，假设项目已用)
