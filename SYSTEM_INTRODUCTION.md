# 智能新闻分析与连续剧追踪系统 (Smart News Analysis & Series Tracking System)

## 1. 系统简介
本项目是一个基于大语言模型（LLM）的智能新闻聚合与分析平台。旨在解决信息过载问题，从海量杂乱的财经新闻中自动提取高价值信息，并将碎片化的单条新闻串联成有脉络的“连续剧”式事件发展史，帮助用户快速把握市场动态和核心事件。

系统采用 **Python (FastAPI)** 作为后端核心，**React** 作为前端展示，内置了双流采集（快讯/深度）、SimHash 去重、FlashText 实体识别以及混合情感分析引擎（规则+LLM）。

## 2. 核心功能

### 2.1 多源采集与预处理
*   **双流采集**：
    *   **快讯流 (Flash)**：高频采集（如新浪财经/财联社），秒级更新，捕捉市场瞬时动态。
    *   **深度流 (Article)**：低频采集（如东方财富），获取长篇深度报道。
*   **智能去重**：基于 **SimHash** 算法，有效识别并过滤内容高度相似的重复新闻（海明距离判断）。
*   **实体识别 (NER)**：利用 **FlashText** 算法快速提取新闻中提及的股票、公司、机构等关键实体。

### 2.2 智能分析与评级
*   **混合情感分析**：
    *   **规则引擎**：基于金融情感词典和关键词（如“立案调查”、“业绩预增”）进行快速初筛和评分。
    *   **LLM 深度分析**：调用 DeepSeek 等大模型对重要新闻进行深度理解，提取结构化数据（摘要、影响评分、事件类型）。
*   **价值评分**：基于新闻实质内容进行 1-5 分的重要性打分（Impact Score），高分新闻视觉高亮。

### 2.3 连续剧式主题追踪 (Series Tracking)
*   **自动聚合**：利用 LLM 提取的 `event_tag`（事件标签），自动将相关联的新闻聚合在一起。
*   **时间轴展示**：以时间轴形式展示特定事件（如“OpenAI人事变动”）的发展脉络。

### 2.4 实时监控台 & 可视化
*   **实时情报流**：支持快讯/深度两种视图模式，实时推送最新消息。
*   **数据可视化**：展示新闻情感分布、热门实体云图、每日趋势统计。
*   **关注配置**：支持自定义关注关键词（Watchlist），优先展示相关内容。

## 3. 技术架构

### 3.1 架构图示
```mermaid
graph TD
    subgraph Data Ingestion [数据采集层]
        A1[Sina Collector (快讯)] -->|SimHash去重| P[Processor]
        A2[EastMoney Collector (深度)] -->|SimHash去重| P
    end

    subgraph Backend [FastAPI 后端 :8000]
        P -->|FlashText NER & 规则评分| DB[(SQLite 数据库)]
        SCH[Scheduler] -->|定时触发| AN[Analysis Worker]
        AN -->|调用| LLM[DeepSeek API]
        LLM -->|结构化结果| DB
    end

    subgraph Frontend [React 前端 :5173]
        F[Web UI] -->|REST API| B(FastAPI Server)
        F -->|展示| NEWS[新闻列表]
        F -->|展示| STATS[统计看板]
        F -->|展示| SERIES[事件追踪]
    end
```

### 3.2 技术栈
*   **后端 (Server)**
    *   **Runtime**: Python 3.11+
    *   **Framework**: FastAPI
    *   **Database**: SQLite 3 (`server_py/news.db`)
    *   **Scheduler**: APScheduler (定时任务)
    *   **NLP Tools**: SimHash (去重), FlashText (NER)
    *   **Data Source**: Akshare (财经数据接口)
    *   **AI Service**: DeepSeek API (兼容 OpenAI SDK)
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
│   ├── collectors/         # 数据采集器 (Sina, EastMoney)
│   ├── venv/               # Python 虚拟环境
│   ├── main.py             # API 入口 & 路由
│   ├── analyzer.py         # LLM 分析任务 Worker
│   ├── processor.py        # 预处理引擎 (清洗, 去重, NER)
│   ├── database.py         # 数据库操作
│   ├── models.py           # Pydantic 数据模型
│   ├── config.py           # 配置加载
│   └── requirements.txt    # Python 依赖
├── .trae/documents/        # 详细设计文档 (Module A-D)
├── start.ps1               # Windows 一键启动脚本
├── start.sh                # Linux/Mac 一键启动脚本
└── SYSTEM_INTRODUCTION.md  # 本文档
```

## 5. 快速开始

### 5.1 环境要求
*   Node.js >= 18 (前端)
*   Python >= 3.11 (后端)
*   DeepSeek API Key (配置在 `server_py/.env`)

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
| `GET` | `/api/news` | 获取新闻列表 (支持分页, type, min_impact 筛选) |
| `POST` | `/api/news` | 接收单条新闻数据 |
| `POST` | `/api/news/batch` | 批量接收新闻数据 |

### 6.2 统计与分析
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | 获取系统统计数据（总数、待分析数、活跃事件等） |
| `GET` | `/api/entities` | 获取热门实体（股票/公司）列表 |
| `GET` | `/api/analysis/status` | 查看后台分析 Worker 状态 |
| `POST` | `/api/analysis/control` | 启动/暂停分析任务 |

### 6.3 专题与分类
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/series` | 获取所有聚合的新闻专题列表 |
| `GET` | `/api/series/{tag}` | 获取指定专题下的所有新闻 |

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
    *   `tags`, `entities`: JSON 格式的标签和实体
    *   `analysis`: LLM 分析结果
    *   `simhash`: 用于去重的哈希值

2.  **`watchlist` 表**：用户关注词配置。

## 8. 常见问题 (FAQ)

**Q: 为什么后端启动报错 `WinError 10022`？**
A: 这是在某些受限环境（如沙箱）下 asyncio 的兼容性问题。代码中已包含针对 Windows 的 `SelectorEventLoopPolicy` 修复，请确保使用最新的代码。

**Q: 数据采集是实时的吗？**
A: 是的。系统启动后，后台调度器会每 30 秒轮询一次快讯源，每 5 分钟轮询一次深度新闻源。

**Q: 如何清空数据？**
A: 删除 `server_py/news.db` 文件，重启后端服务即可。
