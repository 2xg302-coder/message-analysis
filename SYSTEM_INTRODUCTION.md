# 智能新闻分析与连续剧追踪系统 (Smart News Analysis & Series Tracking System)

## 1. 系统简介
本项目是一个基于大语言模型（LLM）的智能新闻聚合与分析平台。旨在解决信息过载问题，从海量杂乱的财经新闻中自动提取高价值信息，并将碎片化的单条新闻串联成有脉络的“连续剧”式事件发展史，帮助用户快速把握市场动态和核心事件。

## 2. 核心功能

### 2.1 智能分析与去噪
*   **自动去噪**：自动识别并过滤广告、水文和低价值信息。
*   **客观评分**：基于新闻实质内容进行 0-10 分的重要性打分，高分新闻（≥8分）视觉高亮。
*   **结构化提取**：
    *   **智能摘要**：生成 <50 字的客观事实摘要。
    *   **关键实体**：自动提取提及的公司、人物、机构等。
    *   **事件标签**：自动归类事件类型（如：财报业绩、监管政策）。

### 2.2 连续剧式主题追踪 (Series Tracking)
*   **自动聚合**：利用 LLM 提取的 `event_tag`（事件标签）和 `topic`（主题），自动将相关联的新闻聚合在一起。
*   **时间轴展示**：以时间轴形式展示特定事件（如“OpenAI人事变动”）的发展脉络，从起因到结果一目了然。
*   **关联推荐**：在单条新闻卡片中直接跳转至对应的事件连续剧视图。

### 2.3 实时监控台 & 配置
*   **任务状态监控**：实时显示后台分析任务的运行状态（运行中/暂停）、当前正在分析的新闻标题。
*   **数据统计**：展示新闻采集总量、已分析数量、评分分布（高分/中分/低分）及活跃事件数。
*   **关注配置**：支持自定义关注关键词（Watchlist），系统将优先展示相关内容（前端支持）。

## 3. 技术架构

### 3.1 架构图示
```mermaid
graph TD
    A[自动采集器 (Akshare)] -->|定时抓取| B(FastAPI 后端)
    B -->|存储原始数据| C[(SQLite 数据库)]
    D[后台分析 Worker] -->|轮询未分析数据| C
    D -->|调用| E[DeepSeek LLM API]
    E -->|返回结构化分析结果| D
    D -->|更新分析结果| C
    F[React 前端] -->|GET /api/news| B
    F -->|GET /api/series| B
    F -->|GET /api/stats| B
    F -->|GET/POST /api/watchlist| B
```

### 3.2 技术栈
*   **后端 (Server)**
    *   **Runtime**: Python 3.9+
    *   **Framework**: FastAPI
    *   **Database**: SQLite 3
    *   **Scheduler**: APScheduler (定时任务)
    *   **Data Source**: Akshare (财经数据接口)
    *   **AI Service**: DeepSeek API (兼容 OpenAI SDK)
*   **前端 (Client)**
    *   **Framework**: React 18 + Vite
    *   **UI Library**: Ant Design 5
    *   **HTTP Client**: Axios

## 4. 项目结构

```
message-analysis/
├── client/                 # 前端项目 (React)
├── server_py/              # 后端服务 (FastAPI)
│   ├── main.py             # API 入口 & 路由
│   ├── analyzer.py         # 分析任务 Worker
│   ├── collector.py        # 数据采集器
│   ├── database.py         # 数据库操作
│   ├── llm_service.py      # LLM 接口封装
│   ├── config.py           # 配置加载
│   └── requirements.txt    # Python 依赖
├── extension/              # (可选) Chrome 采集插件
├── start.sh                # 一键启动脚本
└── SYSTEM_INTRODUCTION.md  # 本文档
```

## 5. 快速开始

### 5.1 环境要求
*   Node.js >= 16 (前端)
*   Python >= 3.8 (后端)
*   DeepSeek API Key (配置在 `server_py/.env`)

### 5.2 一键启动 (推荐)
本项目提供了一键启动脚本，可自动处理依赖安装并同时启动前后端服务。

```bash
# 赋予执行权限（仅首次）
chmod +x start.sh

# 启动服务
./start.sh
```
启动后，访问：
*   **前端页面**: http://localhost:5173
*   **后端 API**: http://localhost:3001/docs (Swagger UI)

### 5.3 手动启动
如果不使用脚本，可以分别启动前后端。

**启动后端**:
```bash
cd server_py
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 并配置 API Key
python main.py
```

**启动前端**:
```bash
cd client
pnpm install
pnpm dev
```

## 6. API 接口文档

后端基于 FastAPI 开发，启动后访问 `http://localhost:3001/docs` 可查看交互式 API 文档。

### 6.1 新闻管理
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `POST` | `/api/news` | 接收单条新闻数据（通常由采集器调用） |
| `POST` | `/api/news/batch` | 批量接收新闻数据 |
| `GET` | `/api/news` | 获取最新新闻列表（支持 source 过滤） |

### 6.2 统计与分析
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `GET` | `/api/stats` | 获取系统统计数据（总数、评分分布、趋势） |
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

系统使用 SQLite 数据库 (`server/news.db`)，主要包含两张表：

1.  **`news` 表**：存储所有新闻数据。
    *   `id`: 唯一标识
    *   `title`, `content`: 标题和内容
    *   `analysis`: LLM 分析结果（JSON 格式，包含 score, event_tag 等）
    *   `created_at`: 入库时间

2.  **`watchlist` 表**：存储用户配置的关注词。
    *   `keyword`: 关键词（主键）
    *   `created_at`: 创建时间

## 8. 配置说明

配置文件位于 `server_py/.env`，主要配置项如下：

```ini
# DeepSeek API 配置
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## 9. 常见问题 (FAQ)

**Q: 为什么分析任务不执行？**
A: 请检查 `server_py/.env` 中是否配置了正确的 `DEEPSEEK_API_KEY`。如果没有 API Key，分析 Worker 会自动暂停。

**Q: 为什么前端显示“暂无数据”？**
A: 请确认后端服务已启动，并且数据采集器（Collector）已运行至少一次。可以查看后端控制台日志确认是否有数据入库。

**Q: 如何清空数据重新开始？**
A: 删除 `server/news.db` 文件，重启后端服务即可自动重新初始化数据库。
