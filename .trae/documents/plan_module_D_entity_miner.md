# 模块 D: 实体共现挖掘 (Entity Miner)

## 1. 目标
实时监测最近 N 小时（如 2 小时）的新闻流，发现高频共现的实体组合，快速捕捉突发事件与市场热点。

## 2. 独立性说明
- **输入**：`news` 表中最近时间段的记录（包含 `entities` 字段）。
- **输出**：实体共现网络图（Nodes, Edges, Weights）或高频簇（JSON）。
- **依赖**：SQLite 读取（pandas.read_sql），NetworkX 图算法。

## 3. 实现步骤

### 3.1 实体抽取与矩阵构建 (`server_py/services/entity_miner.py`)
- 创建 `EntityMiner` 类。
- 实现 `fetch_recent_entities(hours=2)`：
    - 从 SQLite 查询 `datetime('now', f'-{hours} hours')` 内的新闻。
    - 提取每条新闻的 `entities` 字段（假设已由 FlashText 解析为 list）。
- 实现 `build_cooccurrence_matrix(entity_lists)`：
    - 遍历新闻列表，统计实体对出现的频率。
    - 过滤低频词（Threshold < 3）。
    - 构建邻接矩阵或 NetworkX Graph。

### 3.2 社区发现与异常检测
- 实现 `detect_communities(graph)`：
    - 使用 Louvain 算法或 Label Propagation 算法划分社区（Clusters）。
    - 每个社区代表一个相关性极强的事件（如 ["台积电", "地震", "产能"]）。
- 实现 `get_top_edges(limit=20)`：
    - 返回权重最高的边，用于前端展示核心关联。

### 3.3 API 接口开发 (`server_py/routers/analysis.py`)
- `GET /api/analysis/entity-graph`：
    - 参数：`hours` (默认 2)。
    - 返回：JSON Graph { nodes: [...], links: [...] }，适配 ECharts 或 D3.js。
- `GET /api/analysis/hot-clusters`：
    - 返回：Top N 个实体簇。

### 3.4 性能优化
- 使用 `lru_cache` 缓存计算结果（TTL=5分钟），避免频繁重算。
- 异步执行挖掘任务，不阻塞 API 响应。

## 4. 测试计划
- 编写共现矩阵测试 `tests/test_entity_miner.py`，构造 mock 新闻数据。
- 验证算法在 1000 条数据规模下的耗时（< 1s）。
