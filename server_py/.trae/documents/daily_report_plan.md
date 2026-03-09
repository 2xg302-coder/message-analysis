# 每日报告功能开发计划

本计划旨在为系统添加“每日报告”功能，基于现有数据自动生成包含采集统计、热点分析和事件追踪变化的报告。

## 1. 目标
实现一个 API 接口，返回指定日期（默认为昨日）的系统运行报告，包含以下内容：
1.  **昨日采集和分析情况**：新闻采集总量、来源分布、情感倾向分布。
2.  **昨日热点**：高影响力新闻摘要、热门标签/实体。
3.  **历史追踪事件的变化情况**：昨日新增的事件节点（Storyline）及其所属的事件系列（Series）。

## 2. 技术方案

### 2.1 新增 `DailyReportService` 服务
在 `server_py/services/daily_report_service.py` 中创建 `DailyReportService` 类，封装报告生成逻辑。

**主要功能点：**
- **采集统计**：查询 `News` 表，统计指定日期范围内的数据。
    - 总量统计
    - 来源（Source）分组统计
    - 情感（Sentiment）分组统计（基于 `sentiment_score` 划分：正面/中性/负面）
- **热点提取**：
    - 获取高影响力新闻（Impact Score Top N）
    - 统计热门标签（复用或参考 `NewsService.get_tag_stats`）
- **追踪事件监控**：
    - 查询 `Storyline` 表，获取指定日期新增的节点
    - 关联查询 `Series` 表，展示事件脉络的更新

### 2.2 新增 API 路由
在 `server_py/routers/reports.py` 中新增路由模块。

**接口定义：**
- `GET /api/reports/daily`
    - **参数**：`date` (可选，格式 YYYY-MM-DD，默认为昨日)
    - **返回**：JSON 格式的结构化报告数据

### 2.3 集成到主应用
- 在 `server_py/main.py` 中注册新的 `reports` 路由。

## 3. 实施步骤

### Step 1: 创建 `DailyReportService`
- [ ] 创建 `server_py/services/daily_report_service.py` 文件。
- [ ] 实现 `get_collection_stats(date)` 方法：统计采集量、来源和情感。
- [ ] 实现 `get_hotspots(date)` 方法：获取高分新闻和热词。
- [ ] 实现 `get_series_updates(date)` 方法：查询新增的 Storyline 和 Series。
- [ ] 实现 `generate_report(date)` 方法：聚合上述数据。

### Step 2: 创建 API 路由
- [ ] 创建 `server_py/routers/reports.py` 文件。
- [ ] 定义 API 模型（Pydantic models）用于响应结构。
- [ ] 实现 `GET /daily` 接口，调用 `DailyReportService`。

### Step 3: 注册与测试
- [ ] 在 `server_py/main.py` 中引入并注册 `reports_router`。
- [ ] 启动服务，调用接口测试生成的报告数据是否准确。

## 4. 数据结构预览 (JSON)
```json
{
  "date": "2023-10-27",
  "collection_stats": {
    "total_news": 150,
    "sources": {"ITHome": 100, "CCTV": 50},
    "sentiment": {"positive": 40, "neutral": 80, "negative": 30}
  },
  "hotspots": {
    "top_news": [
      {"title": "...", "score": 5, "summary": "..."}
    ],
    "hot_tags": ["AI", "芯片", "新能源"]
  },
  "series_updates": [
    {
      "series_title": "美联储加息路径",
      "new_storyline": "美联储宣布暂停加息..."
    }
  ]
}
```
