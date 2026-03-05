# 模块 B：采集与预处理流水线 (Ingestion Pipeline)

**目标**：实现双流采集（快讯/深度），并进行高效率的预处理（去重、清洗、NER）。

## 1. 采集器升级 (`server_py/collector.py` -> `server_py/collectors/`)

### 新增 `SinaCollector`
- **接口**：AkShare `stock_telegraph_cls` (财联社) 或 `stock_info_global_sina`。
- **目标**：7x24 小时快讯。
- **逻辑**：
  - 定时轮询 (interval=30s)。
  - 解析 `title` 和 `content` (快讯内容)。
  - 提取 `tags` (财联社数据通常包含标签)。
  - 标记 `type='flash'`。

### 改造 `EastMoneyCollector`
- **接口**：AkShare `stock_news_em_general`。
- **目标**：深度新闻。
- **逻辑**：
  - 定时轮询 (interval=5m)。
  - 标记 `type='article'`。

## 2. 预处理引擎 (`server_py/processor.py`)

### 2.1 SimHash 去重
- **算法**：使用 Python `simhash` 库或手动实现。
- **逻辑**：
  - 对每条新闻计算 SimHash 值。
  - 在 DB 中检查是否存在 Hamming Distance <= 3 的旧新闻。
  - 如果存在且时间差 < 1 小时，则视为重复，丢弃或合并。

### 2.2 文本清洗
- **正则库**：
  - 去除 `【免责声明】...`。
  - 去除 `(记者 xxx)` 等署名信息。
  - 去除 HTML 标签 `<.*?>`。

### 2.3 快速实体识别 (NER)
- **工具**：`flashtext` (KeywordProcessor)。
- **词典源**：
  - AkShare `stock_zh_a_spot_em` (A股列表)。
  - AkShare `stock_us_spot_em` (美股列表)。
  - 手动维护的机构/人物列表 (JSON文件)。
- **逻辑**：
  - 加载词典到 `KeywordProcessor`。
  - 对新闻全文进行 `extract_keywords`。
  - 将匹配到的实体存入 `entities` 字段。

### 2.4 初步评级 (Rule-based)
- **规则库**：
  - 关键词匹配 -> `impact_score`。
  - 例：`"立案调查"` -> score=5, sentiment=-0.8。
  - 例：`"业绩预增"` -> score=4, sentiment=0.6。
