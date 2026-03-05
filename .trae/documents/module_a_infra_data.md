# 模块 A：基础设施与数据层 (Infrastructure & Data)

**目标**：建立统一的 Python 后端架构，定义数据库 Schema，清理旧代码。

## 1. 代码清理
- [x] 删除 `server/` 目录。
- [x] 检查根目录 `package.json`，移除与 Node.js 后端相关的脚本（如 `start:server`）。
- [x] 确保 `server_py/` 是唯一的后端入口。

## 2. 数据库 Schema 升级 (`server_py/database.py`)

### 新增字段定义
我们需要修改 `news` 表，或者创建一个新的 `news_v2` 表并迁移数据。

```sql
ALTER TABLE news ADD COLUMN type TEXT DEFAULT 'article'; -- 'flash' | 'article'
ALTER TABLE news ADD COLUMN tags TEXT; -- JSON array: ["宏观", "半导体"]
ALTER TABLE news ADD COLUMN entities TEXT; -- JSON object: {"AAPL": "Apple"}
ALTER TABLE news ADD COLUMN impact_score INTEGER; -- 1-5
ALTER TABLE news ADD COLUMN sentiment_score REAL; -- -1.0 to 1.0
ALTER TABLE news ADD COLUMN simhash TEXT; -- 64-bit hash hex string
```

### 数据模型类 (Pydantic)
在 `server_py/models.py` (需新建) 中定义：

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class NewsItem(BaseModel):
    id: str
    title: str
    content: str
    link: str
    time: str
    source: str
    type: str = "article"
    tags: List[str] = []
    entities: Dict[str, str] = {}
    impact_score: int = 0
    sentiment_score: float = 0.0
    simhash: Optional[str] = None
```

## 3. API 接口定义 (`server_py/main.py`)

### 路由规划
- `GET /api/news`: 获取新闻列表
  - 参数: `limit`, `offset`, `type` (flash/article), `min_impact` (1-5)
- `GET /api/stats`: 获取统计数据（今日利好/利空比例，热门实体）
- `GET /api/entities`: 获取系统识别到的热门实体列表

### 依赖库
确保 `server_py/requirements.txt` 包含：
- `fastapi`
- `uvicorn`
- `pydantic`
- `sqlite-utils` (可选，或原生 sqlite3)
