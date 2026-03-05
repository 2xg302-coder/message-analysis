# 计划：接入 AKShare 财经日历与预期事件匹配

## 目标
接入 AKShare 财经日历，筛选出重要性（星级）大于等于 3 星的事件，生成“日历预期词典”（Expected Events Map），并与实时新闻流进行匹配打分。同时，**新增 API 路由**以供前端获取预期事件数据。

## 实施步骤

### 1. 创建财经日历采集器 (Calendar Collector)
- **文件**: `server_py/collectors/calendar_collector.py`
- **类名**: `CalendarCollector`
- **功能**:
    - 使用 `akshare` 获取每日财经日历数据（优先尝试 `news_economic_baidu` 或 `news_economic_jin10`）。
    - 筛选 `importance`（重要性/星级） >= 3 的事件。
    - 生成并保存“日历预期词典”到 `data/expected_events.json`。
    - 提供 `get_events(date)` 方法供外部调用。

### 2. 新增 API 路由 (New Route)
- **文件**: `server_py/routers/calendar.py` (新建)
- **功能**:
    - `GET /api/calendar/today`: 获取今日预期事件列表。
    - `POST /api/calendar/refresh`: 手动触发日历数据更新。
- **集成**: 在 `server_py/main.py` 中注册该路由。

### 3. 实现事件匹配逻辑 (Event Matching Logic)
- **文件**: `server_py/processor.py`
- **更新内容**:
    - 在 `NewsProcessor` 中增加 `match_expected_events` 方法。
    - 加载 `data/expected_events.json` 中的当日预期事件。
    - **匹配规则**:
        - 对比新闻内容是否包含预期事件的关键词（如“CPI”、“非农”等）。
        - 结合时间窗口（如事件发布时间前后 1 小时内的新闻权重更高）。
    - **处理结果**:
        - 若匹配成功，显著提升新闻的 `impact_score`。
        - 添加特定标签（如 `预期事件: 美国CPI`）。

### 4. 集成到数据采集流水线 (Ingestion Pipeline)
- **文件**: `server_py/services/ingestion.py`
- **更新内容**:
    - 引入 `CalendarCollector`。
    - 添加定时任务，确保每日更新预期事件表。

### 5. 验证与测试
- **测试**: 调用 `GET /api/calendar/today` 确认数据返回。
- **测试**: 手动触发 `POST /api/calendar/refresh`。
- **验证**: 模拟一条包含预期事件关键词的新闻，验证其评分和标签是否正确生成。

## 技术细节
- **数据源**: `akshare` (Baidu/Jin10 财经日历接口)。
- **数据结构示例**:
  ```json
  {
    "2024-05-20": [
      {
        "time": "09:30",
        "country": "中国",
        "event": "一年期贷款市场报价利率",
        "importance": 3,
        "previous": "3.45%",
        "consensus": "3.45%"
      }
    ]
  }
  ```
