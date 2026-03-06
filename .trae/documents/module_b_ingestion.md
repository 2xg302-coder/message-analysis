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

### 2.1 SimHash 去重与优选
- **算法**：使用 Python `simhash` 库 + 文本包含关系检测。
- **逻辑**：
  - 对每条新闻计算 SimHash 值。
  - **去重**：在内存缓存（最近24小时）中检查是否存在 Hamming Distance <= 3 的旧新闻，若存在则视为重复并丢弃。
  - **优选（新增）**：检查文本包含关系。
    - 若新新闻是旧新闻的子集（且长度较短），视为重复，丢弃新新闻。
    - 若旧新闻是新新闻的子集（且长度较短），视为旧新闻信息量不足，**删除旧新闻**，保留新新闻。
  - 目的：自动去除“快讯短标题”或“重复推送”，保留信息量最全的版本。

### 2.2 文本清洗
- **正则库**：
  - 去除 `【免责声明】...`。
  - 去除 `(记者 xxx)` 等署名信息。
  - 去除 HTML 标签 `<.*?>`。
  - **新增**：去除来源前缀（如“财联社3月6日电，”）。
  - **新增**：去除标题括号包裹（如“【...】”），防止因格式不同导致的指纹差异。

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
