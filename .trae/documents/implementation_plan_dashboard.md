# 实施计划：财经新闻数据展示页面

本计划旨在为现有的财经新闻分析系统构建一个前端可视化页面，并增强后端 API 以支持更丰富的数据筛选功能。

## 1. 后端 API 增强 (Python/FastAPI)

为了满足前端的筛选需求（如按标签“加息”、“黄金”筛选），需要对现有 API 进行升级。

### 1.1 修改 `server_py/services/news_service.py`
- [ ] 更新 `get_news` 方法，增加以下参数：
    - `tag` (str, optional): 用于筛选包含特定标签的新闻。
    - `keyword` (str, optional): 用于搜索标题或内容。
    - `start_date` / `end_date` (str, optional): 用于按时间范围筛选。
- [ ] 优化 SQL 查询逻辑，支持上述新的筛选条件。
    - 使用 `LIKE` 操作符匹配 JSON 存储的 `tags` 字段。

### 1.2 修改 `server_py/routers/news.py`
- [ ] 更新 `read_news` 端点，接收新的查询参数 (`tag`, `keyword`, `start_date`, `end_date`) 并传递给 service 层。
- [ ] 增加一个新的端点 `GET /api/tags`，用于获取系统中最热门的标签列表，供前端侧边栏使用。

## 2. 前端项目初始化 (React + Vite)

创建一个现代化的前端项目，用于展示积累的数据。

### 2.1 项目搭建
- [ ] 在项目根目录下创建 `client_web` 目录。
- [ ] 使用 `pnpm create vite` 初始化项目 (React + TypeScript)。
- [ ] 安装核心依赖：
    - `antd`: UI 组件库
    - `axios`: HTTP 请求
    - `react-router-dom`: 路由管理
    - `dayjs`: 日期处理
    - `@ant-design/icons`: 图标库

### 2.2 基础配置
- [ ] 配置 `vite.config.ts`，设置开发服务器代理 (Proxy)，将 `/api` 请求转发到后端 `http://localhost:8000`。
- [ ] 配置全局样式和 Ant Design 主题。

## 3. 前端页面开发

### 3.1 布局与路由 (Layout)
- [ ] 创建 `MainLayout` 组件，包含：
    - 顶部导航栏：显示系统标题、全局搜索框。
    - 侧边栏：显示“热门标签”（如宏观、黄金、战争）、“热门实体”。
    - 内容区域：路由出口。

### 3.2 新闻列表页 (Home/Feed)
- [ ] 开发 `NewsList` 组件：
    - 支持无限滚动或分页加载。
    - 顶部工具栏：显示当前筛选条件，支持按时间/热度排序。
- [ ] 开发 `NewsCard` 组件：
    - 展示标题、摘要、发布时间、来源。
    - **视觉强调**：根据 `impact_score` (影响分) 显示不同的边框颜色或徽标（如 5分红色高亮）。
    - **标签展示**：展示 `tags` 和 `entities`，点击标签可触发筛选。
    - **情感展示**：根据 `sentiment_score` 显示红(利好)/绿(利空)指示条。

### 3.3 数据交互集成
- [ ] 创建 `api.ts` 封装后端请求。
- [ ] 实现前端与后端的联调，确保筛选、搜索功能正常。

## 4. 验证与交付
- [ ] 启动后端服务。
- [ ] 启动前端服务，验证页面能否正确加载数据库中的历史数据。
- [ ] 测试筛选功能（如点击“黄金”标签，只显示相关新闻）。
