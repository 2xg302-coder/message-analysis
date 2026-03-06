# 系统说明文档编写计划 (System Documentation Implementation Plan)

本计划旨在编写一份综合性的系统说明文档 `SYSTEM_DESIGN_AND_FLOW.md`，涵盖**智能新闻分析与连续剧追踪系统**的用户界面 (UI)、核心代码逻辑以及数据流转过程。

## 1. 文档结构设计 (Documentation Structure Design)

* **文件名称**: `SYSTEM_DESIGN_AND_FLOW.md`

* **语言**: 中文 (Chinese)

* **章节规划**:

  1. **项目概述 (Project Overview)**: 简要介绍系统的核心功能（新闻聚合、智能分析、连续剧追踪）。
  2. **系统架构 (System Architecture)**: 描述前后端分离架构、数据库及外部数据源。
  3. **前端界面与交互 (Frontend UI & Interaction)**:

     * 技术栈: React, Vite, Ant Design.

     * 核心页面:

       * **快讯/深度新闻流 (NewsFeed)**: 实时刷新、模式切换。

       * **财经日历 (CalendarView)**: 每日重大经济事件展示与过滤。

       * **数据探索 (DataExplorer)**: 统计分析与可视化。

       * **连续剧追踪 (SeriesView)**: 特定事件的持续跟踪。

     * 关键组件: NewsCard (新闻卡片), Sidebar (侧边导航)。
  4. **后端逻辑与数据流 (Backend Logic & Data Flow)**:

     * **数据采集 (Ingestion)**: 采集器 (Sina, Eastmoney, Calendar) 通过 `akshare` 获取数据。

     * **数据处理 (Processing)**: `processor.py` 负责清洗、去重 (Simhash)、实体识别 (FlashText)、情感/影响力打分。

     * **存储层 (Storage)**: SQLite 数据库 + SQLModel (ORM) 定义数据模型。

     * **API 接口层 (API Layer)**: FastAPI 提供 `/api/news`, `/api/calendar` 等接口。
  5. **核心模块详解 (Key Modules)**:

     * **调度器 (Scheduler)**: APScheduler 定时任务管理。

     * **LLM 服务 (LLM Service)**: 大模型分析集成 (如适用)。
  6. **部署与运行 (Deployment & Running)**:

     * 环境依赖 (Python, Node.js, pnpm)。

     * 启动命令说明。

## 2. 信息收集与确认 (Information Gathering)

* **前端**:

  * `NewsFeed.jsx`: 实时新闻流，支持自动轮询。

  * `CalendarView.jsx`: 财经日历展示，含重要性过滤。

  * `DataExplorer.jsx`: 数据可视化面板。

* **后端**:

  * `server_py/collectors/`: 数据源采集逻辑。

  * `server_py/services/processor.py`: 核心清洗与打分逻辑。

  * `server_py/models_orm.py`: 数据库表结构定义。

  * `server_py/routers/`: API 路由定义。

## 3. 执行步骤 (Implementation Steps)

* [ ] 创建 `SYSTEM_DESIGN_AND_FLOW.md` 文件，包含上述结构。

* [ ] 编写 "项目概述" 和 "系统架构" 部分。

* [ ] 详细描述 "前端界面与交互"，包括页面功能和用户操作流程。

* [ ] 深入阐述 "后端逻辑与数据流"，重点解释数据采集管道和处理逻辑。

* [ ] 补充 "核心模块详解" 和 "部署与运行" 指南。

* [ ] 复查文档，确保内容准确、清晰，并符合用户需求。

## 4. 验证 (Verification)

* 确认文档准确反映当前代码库状态。

* 确保所有用户要求（UI、代码逻辑、数据流）均已覆盖。

