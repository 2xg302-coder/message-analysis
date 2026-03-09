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

### 3.5 系统监控 (System Monitor)
- **入口**: 顶部导航栏右侧的状态指示器。
- **功能**:
    - **实时状态**: 显示当前系统是否正在处理数据、是否有积压任务。
    - **监控面板 (Drawer)**: 点击状态图标打开侧边栏，展示详细的运行指标：
        - **采集器状态**: 今日采集量、失败数、待处理队列长度。
        - **分析器状态**: 当前正在分析的任务数、总处理量。
        - **主线统计**: 活跃主线数、今日生成数。

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
4.  **三元组抽取 (Triples Extraction)**:
    - **来源**: `server_py/prompts/__init__.py`
    - **机制**: 在 LLM 分析阶段，要求模型输出 `(Subject, Predicate, Object)` 格式的实体关系三元组（如 `特斯拉 → 扩产 → Model Y`）。这些结构化数据存储在 `triples` 字段中，用于构建微型知识图谱和增强语义理解。
5.  **关注匹配 (Watchlist Matching)**:
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
    - `News`: 存储新闻主体，包括 `content`, `source`, `tags` (JSON), `entities` (JSON), `triples` (JSON), `impact_score` 等。
    - `CalendarEvent`: 存储财经日历数据。
    - `Series`: 存储长期事件系列，包括 `id` (slug), `title`, `description`, `category`, `keywords` (JSON), `status`, `current_summary` (最新进展摘要)。
    - `Storyline`: 存储市场主线，包括 `date`, `title`, `keywords`, `description`, `importance`, `status`, `series_id`, `series_title`, `related_event_ids` (JSON), `related_news_ids` (JSON)。

### 4.4 API 接口 (API Layer)
后端通过 FastAPI 提供服务，主要路由在 `server_py/routers/`：
- `GET /api/news`: 获取新闻列表，支持分页和多维度筛选。
    - **参数**: `limit`, `offset`, `type` (flash/article), `min_impact` (0-10), `sentiment` (positive/negative/neutral), `entity` (核心实体搜索), `tag` (标签搜索), `start_date`, `end_date`。
    - **返回**: `{"total": int, "count": int, "data": [...]}`。
- `GET /api/calendar/today`: 获取今日财经日历。
- `GET /api/storylines/active`: 获取当前活跃的主线。
- `GET /api/storylines/history`: 获取历史归档的主线。
- `GET /api/storylines/series`: 获取所有 Series 列表（支持按状态筛选）。
- `GET /api/storylines/series/{series_id}`: 获取特定 Series 的所有相关 Storyline（按时间倒序）。
- `POST /api/storylines/generate`: 触发指定日期的主线生成（同步）。
- `POST /api/storylines/batch-generate`: 触发批量主线生成（后台异步任务），返回 `task_id`。
- `POST /api/storylines`: 手动创建主线。
- `PUT /api/storylines/{id}/archive`: 归档指定主线。
- `PUT /api/storylines/archive-all`: 归档所有指定日期前的主线。
- `GET /api/stats`: 获取统计数据（用于 DataExplorer）。
- `GET /api/entities`: 获取核心实体排行（用于 Trends 页面的词云）。
    - **参数**: `limit`, `start_date`, `end_date`。
- `GET /api/analysis/entity-graph`: 返回共现网络图数据 (Nodes, Links)，用于前端可视化。
- `GET /api/analysis/hot-clusters`: 返回识别出的高频实体簇。
- `GET /api/analysis/status`: 获取分析器当前运行状态。
- `POST /api/analysis/control`: 控制分析器的启动与停止。
- `GET /api/monitor/stats`: 获取系统监控数据（分析器状态、采集统计、主线统计）。

### 4.5 标签系统 (Tagging System)
系统的标签 (Tags) 采用**混合生成策略**，结合了规则匹配的即时性和 AI 分析的深度。

1.  **规则匹配 (Rule-based)**:
    - **来源**: `server_py/services/processor.py`
    - **机制**: 在新闻入库时即时生成。系统内置关键词库，如检测到“立案调查”自动打上 `监管` 标签，检测到“加息”打上 `宏观` 标签。
2.  **三元组抽取 (Structured Knowledge)**:
    - **来源**: `server_py/services/analyzer.py`
    - **机制**: 提取实体间的结构化关系（主体-动作-客体），比传统标签更能反映事件本质。
3.  **财经日历关联 (Calendar Association)**:
    - **来源**: `server_py/services/processor.py`
    - **机制**: 自动将新闻内容与当天的财经日历事件比对，若匹配则生成格式为 `预期:国家事件` 的标签。
3.  **AI 深度分析 (LLM Analysis)**:
    - **来源**: `server_py/prompts.py`
    - **机制**: 异步调用大模型生成的深度标签，包括 `event_tag`（用于连续剧追踪）和通用分类标签（如“地缘政治”、“半导体”）。这些标签最终会合并入数据库的 `tags` 字段。

### 4.6 主线生成 (Storyline Generation)
- **模块**: `server_py/services/storyline_generator.py`
- **功能**: 利用大模型基于每日财经日历数据和高影响力新闻，自动提取当日核心市场主线，并将其归类到长期跟踪的 Series（连续剧）中。
- **依赖**: `server_py/services/llm_service.py` (通用 LLM 服务封装)。
- **流程**:
    1.  **数据获取**:
        - 从 `CalendarEvent` 表获取当日重要性 >= 2 的事件。
        - 从 `News` 表获取当日高影响力新闻。
        - 获取当前活跃的 `Series` 列表作为上下文（先验知识）。
    2.  **Prompt 构建**: 使用 `server_py/prompts/storyline_prompt.py` 中的模板，将日历数据、新闻数据和现有 Series 数据格式化。
    3.  **LLM 推理**: 调用 LLM 生成 JSON 格式的主线列表。AI 需判断新主线是否属于现有 Series，或者提议创建新的 Series。
    4.  **关联处理**:
        - 若匹配现有 Series，更新其 `updated_at` 时间。
        - 若提议新 Series，创建新的 `Series` 记录。
        - 记录 `related_event_ids` (关联日历事件) 和 `related_news_ids` (关联新闻)。
    5.  **存储**: 将结果存入 `Storyline` 表，状态为 `active`。
    6.  **先验知识更新**: 调用 `update_series_summaries`，利用当天的 Storyline 内容，让 LLM 更新对应 Series 的 `current_summary`，确保长期追踪的摘要是最新的。

### 4.10 跨日连续剧追踪 (Cross-day Series Tracking)
- **目标**: 解决每日生成的孤立主线无法串联的问题，提供基于时间轴的事件发展视图，并维护事件的长期记忆。
- **实现机制**:
    - **Series 实体**: 引入独立的 `Series` 表，存储长期事件的元数据（标题、描述、分类、关键词）。
        - 系统初始化时会加载种子数据 (`server_py/core/seed_data.py`)，包含如“美联储货币政策”、“俄乌冲突”等预定义 Series。
    - **动态归类**: 每日生成 Storyline 时，LLM 会根据内容将其动态归类到合适的 Series 中。
    - **摘要更新 (Prior Knowledge)**: 每次生成新 Storyline 后，系统会自动更新 Series 的 `current_summary` 字段，通过 LLM 总结最新进展。这相当于系统的“长期记忆”，在下一次生成 Storyline 时作为上下文提供给 LLM，提高生成的准确性和连贯性。
    - **前端展示**: 在主线卡片上提供“追踪剧情”入口，点击后通过侧边栏 (Drawer) 展示该 Series 的时间轴 (Timeline) 和最新摘要。

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
    - **Embedding**: 支持本地轻量级模型 `FastEmbed` (BAAI/bge-small-zh-v1.5) 和云端 API (OpenAI/兼容接口) 混合模式。
    - **Vector DB**: ChromaDB (本地持久化存储)。
- **流程**:
    1.  **初始化**: 优先加载本地模型。若加载失败（环境问题），自动回退到在线 API 模式。
    2.  **运行时容错**: 在计算向量时，若本地模型发生运行时错误，自动尝试调用在线 API 进行补救。
    3.  **主线向量化**: 将活跃主线的标题和描述转为向量存入 ChromaDB。
    4.  **新闻查询**: 新闻入库时，将其内容转为向量，在库中检索最相似的主线。
    5.  **标签生成**: 根据检索结果生成 `主线:xxx` 标签，实现自动归类。

### 4.9 实体挖掘 (Entity Mining)
- **模块**: `server_py/services/entity_miner.py`
- **功能**: 实时分析最近 N 小时（默认 2 小时）的新闻流，挖掘实体间的共现关系，发现潜在的热点事件簇。
- **算法**:
    - **共现网络构建**: 遍历新闻的 `entities` 字段，构建实体共现图 (Graph)，边权重代表共现频率。
    - **社区发现**: 使用 Louvain 算法对共现图进行社区划分 (Community Detection)，每个社区代表一个相关性极强的事件簇。
- **接口**:
    - `GET /api/analysis/entity-graph`: 返回共现网络图数据 (Nodes, Links)，用于前端可视化。
    - `GET /api/analysis/hot-clusters`: 返回识别出的高频实体簇。

### 4.11 系统监控 (System Monitoring)
- **模块**: `server_py/routers/monitor.py`
- **功能**: 提供系统运行状态的实时监控数据。
- **接口**: `GET /api/monitor/stats`
    - **返回数据**:
        - **Analyzer**: 运行状态、任务队列、处理计数。
        - **Collection**: 今日采集量、待处理积压、失败数。
        - **Topics**: 主线总数、活跃数、今日生成数。

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

### 5.4 性能优化 (Performance Optimization)
- **高频调度**: 分析任务调度间隔缩短至 5 秒，大幅提升吞吐量。
- **智能并发控制 (Smart Concurrency)**: 
    - 采用动态信号量机制，实时计算空闲槽位并自动填满，确保并发数始终维持在设定上限（默认 8，可配置）。
    - 避免了传统批处理模式下的“短板效应”（即等待最慢的任务完成）。
- **多 Key 负载均衡 (Load Balancing)**:
    - 支持配置多个 `LLM_API_KEY`（逗号分隔）。
    - 系统采用 Round-Robin 策略轮询使用 Key，突破单一 Key 的速率限制 (Rate Limit)。
- **指数退避重试 (Exponential Backoff)**:
    - 针对 API 429/500 错误，采用指数级增长的等待时间（2s -> 4s -> ... -> 60s），避免在服务不稳定时加重负载。
- **速率限制 (Rate Limiting)**:
    - 在任务发射间隙增加微小延迟 (0.5s)，平滑流量峰值，减少触发 429 的概率。

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

### 6.5 运维工具 (Operational Tools)
- **retry_analysis.py**: 
    - 位于 `server_py/` 目录。
    - **用途**: 手动重置失败的分析任务，或触发旧数据的三元组抽取。
    - **命令**:
        ```bash
        # 重置最近 100 条未提取三元组的数据
        python retry_analysis.py --triples --limit=100
        ```
为了解决环境依赖一致性问题（特别是 Python 的 fastembed/onnxruntime 库在不同系统下的兼容性），项目提供了 Docker 支持。

- **适用场景**: 生产环境部署、非 Windows/WSL 开发环境、或者需要纯净隔离环境时。
- **文件结构**:
    - `server_py/Dockerfile`: 后端镜像定义。
    - `client/Dockerfile`: 前端镜像定义。
    - `docker-compose.yml`: 容器编排配置。
- **启动命令**:
    ```bash
    # 在项目根目录执行
    docker-compose up -d --build
    ```
- **服务地址**:
    - 前端: http://localhost:5173
    - 后端: http://localhost:8000
- **注意事项**:
    - 数据库文件 (`news.db`) 和 向量数据库 (`chroma_db`) 通过挂载卷持久化在宿主机的 `server_py/` 目录下。
    - 开发模式下，修改 `server_py` 代码会自动重启后端服务；前端修改也会触发热更新 (HMR)。
