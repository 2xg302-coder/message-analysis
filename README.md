# 智能新闻分析与事件主线系统

一个面向中文财经/科技新闻的分析系统，提供新闻采集、情绪与影响力分析、经济日历、主线生成与监控看板。

## 功能概览

- 新闻采集与入库（多源采集器 + 异步调度）
- 新闻分析（情绪、标签、实体、影响力）
- 经济日历（按日期查询与手动刷新）
- 事件主线（按日生成、历史回溯、归档）
- 监控看板（采集积压、处理状态、主线统计）
- 前后端分离：FastAPI + React + Vite + Ant Design

## 项目结构

```text
message-analysis/
├── server_py/          # Python 后端（FastAPI + SQLite + Chroma）
├── client/             # 前端（React + Vite + Ant Design）
├── extension/          # 浏览器扩展相关代码
├── docker-compose.yml  # 一键容器化启动
├── start.sh            # Linux/macOS 一键本地启动脚本
└── start.ps1           # Windows 一键本地启动脚本
```

## 环境要求

- Python 3.8+
- Node.js 18+
- pnpm（脚本会尝试自动安装）
- Docker / Docker Compose（可选）

## 快速开始

### 方式一：脚本一键启动（推荐）

Linux/macOS:

```bash
chmod +x start.sh
./start.sh
```

Windows PowerShell:

```powershell
./start.ps1
```

启动后默认访问：

- 前端: http://localhost:5173
- 后端: http://localhost:8000

### 方式二：Docker Compose

```bash
docker compose up --build
```

## 手动启动（开发调试）

### 1) 启动后端

```bash
cd server_py
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 2) 启动前端

```bash
cd client
pnpm install
pnpm dev
```

## 环境变量

后端通过 `server_py/config.py` 读取环境变量（支持 `.env`）。常用项：

```env
# 可选：启用 API 鉴权。设置后，所有 API（除 / 和 /health）需携带 X-API-Key
API_SECRET=your_secret

# LLM（用于主线生成等能力）
LLM_API_KEY=...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# Embedding（可选，默认优先本地 embedding）
USE_LOCAL_EMBEDDING=true
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
LOCAL_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

前端若需要自动携带 API Key，可在 `client/.env` 中设置：

```env
VITE_API_SECRET=your_secret
```

## 主要接口（节选）

- `GET /api/news` 新闻列表与筛选
- `GET /api/stats` 统计信息
- `GET /api/entities` 实体排行
- `GET /api/calendar/today` 当日经济日历
- `POST /api/calendar/refresh` 刷新日历
- `GET /api/storylines/active` 活跃主线
- `POST /api/storylines/generate?date=YYYY-MM-DD` 生成某日主线
- `POST /api/storylines/batch-generate?days=7` 批量生成任务
- `GET /api/monitor/stats` 监控看板数据

## 测试

```bash
cd server_py
pytest
```

## 常见问题

- 前端能打开但接口报错：确认后端运行在 `8000`，且 `client/vite.config.js` 代理目标一致。
- 返回 `401 未授权`：说明后端设置了 `API_SECRET`，请在请求头携带 `X-API-Key`，或设置前端 `VITE_API_SECRET`。
- 首次启动较慢：需要初始化数据库、向量库与模型依赖。

## 设计与文档

- `SYSTEM_INTRODUCTION.md`
- `SYSTEM_DESIGN_AND_FLOW.md`
- `TESTING_STRATEGY.md`

