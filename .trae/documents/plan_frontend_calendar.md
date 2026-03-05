# 计划：实现财经日历前端界面

## 目标
在前端项目中添加“财经日历”页面，用于展示从后端获取的高重要性财经事件。

## 实施步骤

### 1. 更新后端 API (Backend)
- **文件**: `server_py/routers/calendar.py`
- **任务**:
    - 添加 `/api/calendar/date/{date_str}` 接口，支持获取指定日期的事件（格式 `YYYY-MM-DD`）。目前只有 `/today`。

### 2. 前端 API 服务 (Frontend Service)
- **文件**: `client/src/services/api.js`
- **任务**:
    - 添加 `fetchCalendarEvents(date)` 方法。
    - 添加 `refreshCalendar()` 方法。

### 3. 创建日历页面组件 (Calendar Page)
- **文件**: `client/src/pages/CalendarView.jsx`
- **功能**:
    - 使用 `Ant Design` 的 `Calendar` 组件或简单列表展示。
    - 展示事件列表：时间、国家、事件名称、重要性（星级）、前值、预期值、公布值。
    - 支持日期切换。
    - 提供“手动刷新”按钮。

### 4. 注册路由与导航 (Router & Navigation)
- **文件**: `client/src/App.jsx`
    - 添加路由 `/calendar` -> `CalendarView`。
- **文件**: `client/src/layouts/MainLayout.jsx`
    - 在侧边栏添加“财经日历”菜单项（图标可使用 `CalendarOutlined`）。

## 预期效果
用户点击侧边栏“财经日历”，可以看到当日或选中日期的财经事件列表，并能手动触发更新。
