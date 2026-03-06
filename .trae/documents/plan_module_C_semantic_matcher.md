# 模块 C: 语义匹配与向量化引擎 (Semantic Matcher)

## 1. 目标
利用轻量级向量数据库（ChromaDB）实现新闻与主线标签的语义匹配，解决关键词匹配的局限性，实现精准追踪。

## 2. 独立性说明
- **输入**：实时新闻文本，活跃主线列表（模块 B 的输出）。
- **输出**：匹配结果（Storyline ID 列表，Confidence Score）。
- **依赖**：ChromaDB（Python SDK），OpenAI Embedding 或本地模型。

## 3. 实现步骤

### 3.1 向量引擎封装 (`server_py/services/vector_store.py`)
- 创建 `VectorStore` 类，封装 ChromaDB 操作。
- 初始化 `chromadb.Client()`（使用本地持久化存储）。
- 支持方法：
    - `add_storylines(storylines)`: 将主线文本转向量并存入 ChromaDB。
    - `query_news_tags(news_text, threshold=0.7)`: 输入新闻文本，查询最匹配的主线标签。
    - `clear_storylines()`: 清空向量库（归档时）。

### 3.2 向量化模型集成
- 推荐使用 OpenAI `text-embedding-3-small` (快速且便宜) 或 HuggingFace 本地模型 (如 `all-MiniLM-L6-v2`)。
- 实现 `embedding_service.py`，提供 `get_embedding(text)` 方法。

### 3.3 新闻处理器集成 (`server_py/services/processor.py`)
- 修改 `NewsProcessor` 类：
    1. 在新闻处理流程中，增加 `_match_storylines(news)` 步骤。
    2. 调用 `VectorStore.query_news_tags(news.content)`。
    3. 若匹配成功且置信度高，将主线 ID 存入新闻的 `tags` 字段（格式如 `storyline:123`）。
- **优化**：对于长新闻，提取摘要后再向量化，提高准确性。

## 4. 测试计划
- 编写向量检索测试 `tests/test_vector_store.py`。
- 验证不同相似度阈值下的匹配效果（Precision/Recall）。
