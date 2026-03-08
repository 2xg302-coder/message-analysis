# 计划：重组系统菜单结构

当前的菜单结构比较扁平，感觉有些混乱。我们将把它重组为逻辑分组，以提高可用性和导航体验。

## 建议的菜单结构

我们将现有的 8 个菜单项分为 3 个主要类别：

1.  **市场监控 (Market Monitor)**
    *   新闻流 (News Feed) - `/`
    *   IT之家 (ITHome) - `/ithome`
    *   财经日历 (Calendar) - `/calendar`

2.  **分析工具 (Analysis Tools)**
    *   趋势分析 (Trends) - `/trends`
    *   每日主线 (Storylines) - `/storylines`
    *   连续剧追踪 (Series Tracking) - `/series`

3.  **数据管理 (Data Management)**
    *   数据资产 (Data Explorer) - `/explorer`
    *   关注配置 (Watchlist) - `/watchlist`

## 实施步骤

1.  **更新 `MainLayout.jsx`**:
    *   导入必要的新组标题图标（例如 `DashboardOutlined`，`LineChartOutlined`，`ToolOutlined` 或重用现有的图标）。
    *   重构 `items` 数组以使用上述嵌套结构。
    *   实现 `openKeys` 状态管理，以确保根据当前 URL 展开正确的子菜单。
    *   保留现有的 `selectedKey` 逻辑以高亮显示活动页面。

## 验证

*   验证菜单是否按新分组渲染。
*   验证点击菜单项是否导航到正确的页面。
*   验证直接加载特定页面（例如刷新 `/series`）时，是否展开了正确的菜单组。
*   验证活动项是否高亮显示。
