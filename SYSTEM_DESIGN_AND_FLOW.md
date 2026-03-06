# 智能新闻分析与连续剧追踪系统说明文档

## 1. 项目概述 (Project Overview)
本项目是一个集**实时新闻聚合**、**智能深度分析**和**事件连续剧追踪**于一体的金融信息系统。它旨在帮助用户从海量碎片化的财经资讯中，快速捕捉市场热点，梳理事件发展脉络，并提供量化的影响力评估。

系统的核心价值在于：
- **全网聚合**：实时采集新浪财经、东方财富、财联社等多渠道数据。
- **智能清洗**：通过 Simhash 去重、FlashText 实体识别等算法，剔除噪音，提取核心价值。
- **量化评分**：对每条新闻进行影响力和情感打分，辅助投资决策。
- **连续剧追踪**：自动聚合相关事件，形成时间线，呈现事件的起因、经过和结果。

## 2. 系统架构 (System Architecture)
系统采用前后端分离的架构设计，确保了组件的解耦和扩展性。

### 架构概览
- **前端 (Frontend)**: 基于 **React 18** + **Vite** 构建，使用 **Ant Design** 作为 UI 组件库。负责数据的实时展示和用户交互。
- **后端 (Backend)**: 基于 **Python FastAPI** 构建，提供高性能的 RESTful API。
- **数据存储 (Database)**: 使用 **SQLite** 作为持久化存储，配合 **SQLModel (SQLAlchemy)** 进行 ORM 映射。
- **数据采集 (Collectors)**: 利用 **akshare** 等工具，定时从外部源（Sina, Eastmoney, Jin10）抓取数据。
- **核心处理 (Processor)**: 包含 NLP 处理流水线（清洗、去重、NER、打分）。

```mermaid
graph TD
    User[用户] --> Frontend[前端 (React)]
    Frontend -->|HTTP API| Backend[后端 (FastAPI)]
    
    subgraph "后端服务 (Backend Services)"
        Backend --> Router[路由层 (Routers)]
        Router --> Service[服务层 (Services)]
        Service --> Processor[数据处理器 (Processor)]
        Service --> Database[(SQLite 数据库)]
        
        Scheduler[调度器 (APScheduler)] --> Collector[采集器 (Collectors)]
        Collector -->|原始数据| Processor
        Processor -->|结构化数据| Database
    end
    
    subgraph "外部数据源 (External Sources)"
        Collector -->|akshare| Sina[新浪财经]
        Collector -->|akshare| Eastmoney[东方财富]
        Collector -->|akshare| Calendar[财经日历]
    end
```

## 3. 前端界面与交互 (Frontend UI & Interaction)

### 3.1 快讯/深度新闻流 (NewsFeed)
- **功能**: 系统的主界面，展示实时更新的财经新闻。
- **模式切换**:
    - **快讯模式 (Flash Mode)**: 类似电报风格，通过 `NewsFlash` 组件展示，强调时效性，适合快速浏览。
    - **深度模式 (Depth Mode)**: 通过 `NewsCard` 组件展示，包含新闻的详细内容、AI 提取的实体、标签以及影响力评分。
- **交互**:
    - **实时轮询**: 页面每 30 秒自动刷新，确保用户看到最新消息。
    - **筛选**: 支持按“重要性”（1-5星）和“来源”进行筛选。

### 3.2 财经日历 (CalendarView)
- **功能**: 展示每日的全球重大经济事件（如 GDP 公布、利率决议）。
- **核心逻辑**:
    - **多源聚合**: 后端支持从百度、金十、新浪等多源采集，并在前端统一展示。
    - **过滤**: 前端实现了基于重要性的过滤（全部 / 2星+ / 3星+），帮助用户聚焦核心事件。
    - **状态标识**: 自动高亮显示已公布的数据，对比前值和预期值。

### 3.3 数据探索 (DataExplorer & Trends)
- **功能**: 系统的“仪表盘”，提供宏观数据的统计与可视化。
- **可视化**:
    - **DataExplorer**: 展示系统整体状态（总数、活跃度）、标签分布和实体排行。
    - **Trends**: 提供更长时间维度的标签热度趋势图，帮助识别市场长期主题。
    - **交互式洞察**: 在 Trends 页面点击任意核心实体标签，会弹出模态框展示该实体的相关新闻列表，支持情感倾向（利好/利空）的可视化标记。

### 3.4 连续剧追踪 (SeriesView)
- **功能**: 针对特定热点事件进行全生命周期的追踪。
- **核心逻辑**:
    - **聚合方式**: 后端通过解析 `News` 表中 `analysis` 字段的 JSON 数据，提取 `event_tag` 进行聚合。
    - **性能优化**: 默认仅分析最近 2000 条数据，兼顾性能与时效性。
- **交互**:
    - **左侧列表**: 显示所有被聚合的“连续剧”事件，按更新时间倒序排列。
    - **右侧时间轴**: 选中事件后，右侧以时间轴形式展示该事件的所有相关报道，清晰呈现事件的发展脉络。
    - **路由联动**: 支持通过 URL 参数直接定位到特定事件。

## 4. 后端逻辑与数据流 (Backend Logic & Data Flow)

### 4.1 数据采集 (Data Ingestion)
采集模块位于 `server_py/collectors/`，主要包含：
- **SinaCollector**: 抓取新浪财经 7x24 快讯和财联社电报。频率：30秒/次。
- **EastmoneyCollector**: 抓取东方财富网的深度新闻。频率：5分钟/次。
- **CalendarCollector**: 每日 08:00 抓取当天的财经日历数据。具备**多源自动降级**机制（首选百度财经，失败则尝试金十数据，最后兜底新浪财经），确保数据获取的高可用性。取消了后端的重要性过滤，全量保留所有事件，交由前端进行灵活筛选。

### 4.2 数据处理流水线 (Processing Pipeline)
数据在 `server_py/services/processor.py` 中经过以下步骤：
1.  **清洗 (Cleaning)**: 去除 HTML 标签、免责声明、广告后缀等噪音。
2.  **去重 (Deduplication)**:
    - **Simhash**: 计算文本指纹，进行海明距离比较，去除高度相似的内容。
    - **时间窗口**: 仅在最近 24 小时的数据中进行比对，提高效率。
3.  **实体识别 (NER)**: 使用 `FlashText` 算法，基于预定义的词库高效提取股票、公司、人物等实体。
4.  **关注匹配 (Watchlist Matching)**:
    - **来源**: `server_py/services/processor.py`
    - **机制**: 实时加载用户配置的关键词，若新闻内容匹配，自动打上 `关注` 标签，并提升 `impact_score` (+2)，确保重要信息不被遗漏。
5.  **语义匹配 (Semantic Matching)**:
    - **来源**: `server_py/services/vector_store.py`
    - **机制**: 对长文本新闻（>20字符）进行向量化，并在 ChromaDB 中检索相似的主线（Storyline）。若匹配度高于阈值（0.45），自动打上 `主线:xxx` 标签，并提升 `impact_score`。
6.  **评分 (Scoring)**:
    - **规则打分**: 根据关键词（如“重磅”、“突发”）和来源权重计算 `impact_score`。
    - **情感分析**: 基于词典匹配计算 `sentiment_score`。

### 4.3 数据存储 (Storage)
- **技术**: SQLite + SQLModel。
- **模型 (`models_orm.py`)**:
    - `News`: 存储新闻主体，包括 `content`, `source`, `tags` (JSON), `entities` (JSON), `impact_score` 等。
    - `CalendarEvent`: 存储财经日历数据。
    - `Storyline`: 存储市场主线，包括 `date`, `title`, `keywords`, `description`, `importance`, `status` (active/archived)。

### 4.4 API 接口 (API Layer)
后端通过 FastAPI 提供服务，主要路由在 `server_py/routers/`：
- `GET /api/news`: 获取新闻列表，支持分页和多维度筛选。
    - **参数**: `limit`, `offset`, `type` (flash/article), `min_impact` (0-10), `sentiment` (positive/negative/neutral), `entity` (核心实体搜索), `tag` (标签搜索), `start_date`, `end_date`。
    - **返回**: `{"total": int, "count": int, "data": [...]}`。
- `GET /api/calendar/today`: 获取今日财经日历。
- `GET /api/storylines/active`: 获取当前活跃的主线。
- `GET /api/storylines/history`: 获取历史归档的主线。
- `POST /api/storylines`: 手动创建主线。
- `PUT /api/storylines/{id}/archive`: 归档指定主线。
- `GET /api/stats`: 获取统计数据（用于 DataExplorer）。
- `GET /api/entities`: 获取核心实体排行（用于 Trends 页面的词云）。
    - **参数**: `limit`, `start_date`, `end_date`。
- `GET /api/series`: 获取连续剧事件列表。

### 4.5 标签系统 (Tagging System)
系统的标签 (Tags) 采用**混合生成策略**，结合了规则匹配的即时性和 AI 分析的深度。

1.  **规则匹配 (Rule-based)**:
    - **来源**: `server_py/services/processor.py`
    - **机制**: 在新闻入库时即时生成。系统内置关键词库，如检测到“立案调查”自动打上 `监管` 标签，检测到“加息”打上 `宏观` 标签。
2.  **财经日历关联 (Calendar Association)**:
    - **来源**: `server_py/services/processor.py`
    - **机制**: 自动将新闻内容与当天的财经日历事件比对，若匹配则生成格式为 `预期:国家事件` 的标签。
3.  **AI 深度分析 (LLM Analysis)**:
    - **来源**: `server_py/prompts.py`
    - **机制**: 异步调用大模型生成的深度标签，包括 `event_tag`（用于连续剧追踪）和通用分类标签（如“地缘政治”、“半导体”）。这些标签最终会合并入数据库的 `tags` 字段。

### 4.6 主线生成 (Storyline Generation)
- **模块**: `server_py/services/storyline_generator.py`
- **功能**: 利用大模型基于每日财经日历数据，自动提取当日 3-5 个核心市场主线。
- **依赖**: `server_py/services/llm_service.py` (通用 LLM 服务封装)。
- **流程**:
    1.  **数据获取**: 从 `CalendarEvent` 表获取当日重要性 >= 2 的事件。
    2.  **Prompt 构建**: 使用 `server_py/prompts/storyline_prompt.py` 中的模板，将日历数据格式化。
    3.  **LLM 推理**: 调用 LLM 生成 JSON 格式的主线列表（包含标题、关键词、描述、影响、重要性）。
    4.  **存储**: 将结果存入 `Storyline` 表，状态为 `active`。

### 4.7 主线管理 (Storyline Manager)
- **模块**: `server_py/services/storyline_manager.py`
- **功能**: 管理每日市场主线（Storyline），支持创建、激活、归档和查询。
- **流程**:
    1.  **生成**: 由 Module A (Daily Storyline) 生成每日主线候选。
    2.  **存储**: 存入 `Storyline` 表，状态默认为 `active`。
    3.  **归档**: 每日定期将旧的主线归档 (`archived`)，保留历史记录。

### 4.8 语义匹配与向量化 (Semantic Matching & Vectorization)
- **模块**: `server_py/services/vector_store.py`
- **功能**: 实现新闻与主线标签的深层语义关联，解决关键词匹配的局限性。
- **技术栈**:
    - **Embedding**: OpenAI `text-embedding-3-small` (推荐) 或兼容 API。
    - **Vector DB**: ChromaDB (本地持久化存储)。
- **流程**:
    1.  **主线向量化**: 将活跃主线的标题和描述转为向量存入 ChromaDB。
    2.  **新闻查询**: 新闻入库时，将其内容转为向量，在库中检索最相似的主线。
    3.  **标签生成**: 根据检索结果生成 `主线:xxx` 标签，实现自动归类。

### 4.9 实体挖掘 (Entity Mining)
- **模块**: `server_py/services/entity_miner.py`
- **功能**: 实时分析最近 N 小时（默认 2 小时）的新闻流，挖掘实体间的共现关系，发现潜在的热点事件簇。
- **算法**:
    - **共现网络构建**: 遍历新闻的 `entities` 字段，构建实体共现图 (Graph)，边权重代表共现频率。
    - **社区发现**: 使用 Louvain 算法对共现图进行社区划分 (Community Detection)，每个社区代表一个相关性极强的事件簇。
- **接口**:
    - `GET /api/analysis/entity-graph`: 返回共现网络图数据 (Nodes, Links)，用于前端可视化。
    - `GET /api/analysis/hot-clusters`: 返回识别出的高频实体簇。

## 5. 核心模块详解 (Key Modules)

### 5.1 调度系统 (Scheduler)
- 使用 `APScheduler` 的 `AsyncIOScheduler`。
- 在 `server_py/services/ingestion.py` 中初始化。
- 负责定时触发各个 Collector 的 `collect()` 方法，并处理并发和错误重试。

### 5.2 数据库连接池 (Database Connection)
- 在 `server_py/core/database_orm.py` 中配置。
- 使用 SQLAlchemy 的 `create_async_engine` 实现异步数据库访问，提高高并发下的响应性能。

### 5.3 启动性能优化 (Startup Optimization)
- **异步数据库初始化**: 将 `server_py/core/database.py` 中的数据库初始化逻辑从同步改为异步，并移除模块导入时的自动执行，改为在 FastAPI `lifespan` 中显式调用，避免阻塞主线程。
- **异步资源加载**: 将情感词典加载 (`server_py/services/analyzer.py`) 改为异步执行，减少启动时的 I/O 阻塞。
- **延迟任务执行**: 在 `server_py/services/ingestion.py` 中，将启动后的立即抓取任务延迟 5 秒执行，优先保证 HTTP 服务端口的快速就绪。

## 6. 部署与运行 (Deployment & Running)

### 6.1 环境要求
- **后端**: Python 3.9+, 依赖包见 `requirements.txt`。
- **前端**: Node.js 16+, pnpm。

### 6.2 启动步骤
1.  **后端启动**:
    ```bash
    cd server_py
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python main.py
    ```
    后端服务将运行在 `http://localhost:8000`。

2.  **前端启动**:
    ```bash
    cd client
    pnpm install
    pnpm run dev
    ```
    前端页面将运行在 `http://localhost:5173`。

### 6.3 配置文件
- 后端配置位于 `server_py/.env` (可参考 `.env.example`)，包含数据库路径、API 密钥等敏感信息。
