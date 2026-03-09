# 智能新闻分析与连续剧追踪系统 (Smart News Analysis & Series Tracking System)

## 1. 系统简介
本项目是一个基于大语言模型（LLM）的智能新闻聚合与分析平台。旨在解决信息过载问题，从海量杂乱的财经新闻中自动提取高价值信息，并将碎片化的单条新闻串联成有脉络的“连续剧”式事件发展史，帮助用户快速把握市场动态和核心事件。

系统采用 **Python (FastAPI)** 作为后端核心，**React** 作为前端展示，内置了双流采集（快讯/深度）、SimHash 去重、FlashText 实体识别以及混合情感分析引擎（规则+LLM）。

## 2. 核心功能

### 2.1 多源采集与预处理
*   **双流采集**：
    *   **快讯流 (Flash)**：高频采集（如新浪财经/财联社），秒级更新，捕捉市场瞬时动态。
    *   **深度流 (Article)**：低频采集（如东方财富），获取长篇深度报道。
*   **智能去重与优选**：
    *   **SimHash 指纹**：基于局部敏感哈希算法，识别内容高度相似的重复新闻。
    *   **包含检测优化**：自动检测“快讯短标题”与“完整长新闻”的包含关系，智能删除信息量不足的旧快讯，保留信息量最全的版本。
*   **深度清洗**：自动去除来源前缀（如“财联社电报”）、标题包裹符号、免责声明等噪音，确保指纹计算的纯净度。
*   **实体识别 (NER)**：利用 **FlashText** 算法快速提取新闻中提及的股票、公司、机构等关键实体。

### 2.2 智能分析与评级
*   **混合情感分析**：
    *   **规则引擎**：基于金融情感词典和关键词（如“立案调查”、“业绩预增”）进行快速初筛和评分。
    *   **LLM 深度分析**：调用 DeepSeek/OpenRouter 等大模型对重要新闻进行深度理解，提取结构化数据（摘要、影响评分、事件类型）及实体关系三元组。
*   **价值评分**：基于新闻实质内容进行 1-5 分的重要性打分（Impact Score），高分新闻视觉高亮。

### 2.4 连续剧式主题追踪 (Series Tracking)
*   **Series 实体管理**：引入独立的 `Series`（连续剧）概念，对长期热点事件（如“美联储货币政策”、“俄乌冲突”）进行持久化追踪。
*   **智能归类**：每日生成的主线（Storyline）会自动归类到对应的 Series 中，或由 LLM 提议创建新的 Series。
*   **先验知识更新**：系统会自动总结每个 Series 的最新进展（Current Summary），作为“长期记忆”辅助后续的分析，确保事件脉络的连贯性。
*   **时间轴展示**：以时间轴形式展示特定 Series 的发展脉络，并提供最新的事件摘要。

### 2.5 财经日历 (Economic Calendar)
*   **多源采集**：自动采集 Baidu/Jin10/Sina 等来源的财经日历数据，具备自动降级容错机制（Baidu -> Jin10 -> Sina），确保数据高可用。
*   **全量采集与前端筛选**：后端采集所有重要性级别的事件，前端提供灵活筛选功能（全部/2星+/3星+），满足不同用户需求。
*   **事件匹配**：将实时新闻与日历事件关联，提升相关新闻的影响力评分。
*   **数据持久化**：日历数据存入数据库，支持历史回溯。

### 2.6 实时监控台 & 可视化
*   **实时情报流**：支持快讯/深度两种视图模式，实时推送最新消息。
*   **DataExplorer (系统仪表盘)**：展示新闻情感分布、热门实体云图。
*   **Trends (趋势分析)**：展示近期的标签/事件热度变化曲线，辅助判断市场风格切换。
*   **交互式实体洞察**：点击“今日核心实体”中的标签（如“英伟达”、“美联储”），可立即弹窗查看与该实体相关的所有新闻详情，帮助用户快速溯源。
*   **关注配置**：支持自定义关注关键词（Watchlist）。系统后端会自动从新闻流中匹配这些关键词，匹配到的新闻将被打上“关注”标签并获得权重提升（Impact Score +2），在前端列表中优先展示。

## 3. 技术架构

### 3.1 架构图示
```mermaid
graph TD
    subgraph Data Ingestion [数据采集层]
        A1[Sina Collector (快讯)] -->|SimHash去重| P[Processor]
        A2[EastMoney Collector (深度)] -->|SimHash去重| P
        SCH[Ingestion Service] -->|调度| A1
        SCH -->|调度| A2
    end

    subgraph Backend [FastAPI 后端 :8000]
        P -->|News Service| DB[(SQLite 数据库)]
        API[API Routers] -->|调用| NS[News Service]
        NS -->|CRUD| DB
        AN[Analysis Worker] -->|获取未分析数据| NS
        AN -->|调用| LLM[DeepSeek API]
        LLM -->|保存结果| NS
    end

    subgraph Frontend [React 前端 :5173]
        F[Web UI] -->|REST API| API
        F -->|展示| NEWS[新闻列表]
        F -->|展示| STATS[统计看板]
        F -->|展示| SERIES[事件追踪]
    end
```

### 3.2 技术栈
*   **后端 (Server)**
    *   **Runtime**: Python 3.11+
    *   **Framework**: FastAPI (全异步架构: Core/Services/Routers)
    *   **Database**: SQLite 3 + aiosqlite (异步数据库访问)
    *   **Scheduler**: APScheduler (异步定时任务)
    *   **NLP Tools**: SimHash (去重), FlashText (NER)
    *   **Data Source**: Akshare (财经数据接口)
    *   **AI Service**: DeepSeek-V3 (默认配置为云端 API，非本地模型)
    *   **Security**: API Key 认证 (可选)
*   **前端 (Client)**
    *   **Framework**: React 18 + Vite
    *   **UI Library**: Ant Design 5
    *   **Charts**: Recharts
    *   **HTTP Client**: Axios

## 4. 项目结构

```
message-analysis/
├── client/                 # 前端项目 (React + Vite)
├── server_py/              # 后端服务 (FastAPI)
│   ├── core/               # 核心基础设施 (日志, 数据库连接)
│   ├── routers/            # API 路由定义 (news, analysis, calendar)
│   ├── services/           # 业务逻辑层 (news_service, ingestion, analyzer, processor)
│   ├── collectors/         # 数据采集器 (Sina, EastMoney, Calendar)
│   ├── models.py           # Pydantic 数据模型
│   ├── main.py             # 应用入口
│   ├── config.py           # 配置加载
│   ├── analyzer.py         # LLM 分析任务 Worker
│   ├── processor.py        # 预处理引擎 (清洗, 去重, NER)
│   └── requirements.txt    # Python 依赖
├── .trae/documents/        # 详细设计文档
├── start.ps1               # Windows 一键启动脚本
├── start.sh                # Linux/Mac 一键启动脚本
└── SYSTEM_INTRODUCTION.md  # 本文档
```

## 5. 快速开始

### 5.1 环境要求
*   Node.js >= 18 (前端)
*   Python >= 3.11 (后端)
*   LLM API Key (配置在 `server_py/.env`)
*   (可选) API_SECRET: 用于保护 API 接口的密钥

### 5.2 一键启动 (Windows)
本项目提供了 PowerShell 启动脚本，自动处理依赖安装并启动服务。

```powershell
# 在项目根目录下运行
.\start.ps1
```
启动后，访问：
*   **前端页面**: http://localhost:5173
*   **后端 API**: http://localhost:8000/docs (Swagger UI)

### 5.3 手动启动

**启动后端**:
```bash
cd server_py
# 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (可选，或直接修改 config.py)
# cp .env.example .env 

# 启动服务
python main.py
```

### 5.4 模型配置说明 (LLM Configuration)

**双模型策略 (Dual Model Strategy)**：
本系统支持配置两个不同的模型：
1.  **Main LLM (主模型)**：用于深度分析 (Standard Analysis)，处理长文本、复杂逻辑。推荐使用 DeepSeek-V3, GPT-4o, Gemini 1.5 Pro 等高性能模型。
2.  **Fast LLM (快速模型)**：用于快讯分析、实体提取 (Fast Analysis)。推荐使用本地 Ollama (Llama 3, Mistral) 或云端小模型 (Gemini Flash, Haiku) 以降低成本和延迟。

请在 `server_py/.env` 文件中配置：

```bash
# === 主模型配置 (Main LLM) ===
# 示例：使用 OpenRouter 接入 Gemini 1.5 Pro
LLM_API_KEY=sk-key1,sk-key2
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemini-2.0-pro-exp-02-05
# 支持多 Key 轮询，逗号分隔

# === 快速模型配置 (Fast LLM) ===
# 示例：使用本地 Ollama 运行 Llama 3
FAST_LLM_API_KEY=ollama
FAST_LLM_BASE_URL=http://localhost:11434/v1
FAST_LLM_MODEL=llama3

# 注意：如果未配置 FAST_LLM，系统将自动降级使用 Main LLM 处理所有任务。
```

**DeepSeek (旧版兼容)**：
系统仍然兼容旧版配置方式（作为主模型）：
```bash
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

**启动前端**:
```bash
cd client
pnpm install
pnpm dev
```

## 6. API 接口文档

后端基于 FastAPI 开发，启动后访问 `http://localhost:8000/docs` 可查看交互式 API 文档。

### 6.1 新闻管理
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/news` | 获取新闻列表 (支持分页, type, min_impact, entity, tag 筛选) |

### 6.2 统计与监控
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | 获取系统统计数据（总数、待分析数、活跃事件等） |
| `GET` | `/api/entities` | 获取热门实体（股票/公司）列表及频次 |
| `GET` | `/api/analysis/status` | 查看后台分析 Worker 状态 |
| `POST` | `/api/analysis/control` | 启动/暂停分析任务 |
| `GET` | `/api/monitor/stats` | 获取系统整体监控数据（分析器、采集器、主线） |

### 6.3 连续剧与主线
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/storylines/active` | 获取当前活跃的主线 |
| `GET` | `/api/storylines/series` | 获取所有 Series 列表 |
| `GET` | `/api/storylines/series/{id}` | 获取特定 Series 的所有 Storylines |
| `POST` | `/api/storylines/generate` | 触发今日主线生成 |

### 6.4 关注配置
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/watchlist` | 获取当前的关注关键词列表 |
| `POST` | `/api/watchlist` | 更新关注关键词列表 |

## 7. 数据库说明

系统使用 SQLite 数据库 (`server_py/news.db`)，主要包含：

1.  **`news` 表**：核心数据表。
    *   `id`: 唯一标识 (SimHash 或 MD5)
    *   `type`: 'flash' (快讯) 或 'article' (深度)
    *   `title`, `content`: 标题和内容
    *   `impact_score`: 影响力评分 (1-5)
    *   `sentiment_score`: 情感评分 (-1.0 ~ 1.0)
    *   `tags`, `entities`, `triples`: JSON 格式的标签、实体和三元组
    *   `analysis`: LLM 分析结果
    *   `simhash`: 用于去重的哈希值

2.  **`watchlist` 表**：用户关注词配置。

3.  **`calendar_events` 表**：财经日历事件。
    *   `date`: 日期 (YYYY-MM-DD)
    *   `time`: 时间
    *   `country`: 国家/地区
    *   `event`: 事件名称
    *   `importance`: 重要性 (0-3)

4.  **`series` 表**：长期连续剧事件。
    *   `id`: 唯一标识 (Slug)
    *   `title`, `description`: 标题与描述
    *   `category`: 分类
    *   `current_summary`: 最新进展摘要（先验知识）

5.  **`storylines` 表**：每日市场主线。
    *   `date`: 日期
    *   `title`, `description`: 标题与描述
    *   `series_id`: 关联的 Series ID
    *   `related_event_ids`: 关联日历事件
    *   `related_news_ids`: 关联新闻

## 8. 常见问题 (FAQ)

**Q: 为什么后端启动报错 `WinError 10022`？**
A: 这是在某些受限环境（如沙箱）下 asyncio 的兼容性问题。代码中已包含针对 Windows 的 `SelectorEventLoopPolicy` 修复，请确保使用最新的代码。

**Q: 数据采集是实时的吗？**
A: 是的。系统启动后，后台调度器会每 30 秒轮询一次快讯源，每 5 分钟轮询一次深度新闻源。

**Q: 如何清空数据？**
A: 删除 `server_py/news.db` 文件，重启后端服务即可。
