# 接入新闻联播与人民日报数据计划

本计划旨在将“新闻联播”和“人民日报”的数据源接入到现有的消息分析系统中。

## 1. 新闻联播采集器 (CCTVCollector)

利用 `akshare` 的 `news_cctv` 接口获取新闻联播文字稿。

- **文件位置**: `server_py/collectors/cctv_collector.py`
- **功能**:
    - `collect()` 方法：
        - 获取当前日期和前一日期的字符串 (YYYYMMDD)。
        - 调用 `ak.news_cctv(date=date_str)` 获取数据。
        - 遍历返回的 DataFrame，提取 `date`, `title`, `content`。
        - 构造标准新闻对象：
            - `source`: 'CCTV'
            - `type`: 'article'
            - `time`: 格式化为 `YYYY-MM-DD HH:MM:SS` (默认为当天 19:00:00)
            - `id`: MD5(content + time)
- **依赖**: `akshare`, `pandas` (akshare 返回 df), `hashlib`, `datetime`.

## 2. 人民日报采集器 (PeopleDailyCollector)

利用 `httpx` 和 `xml.etree.ElementTree` 解析人民日报官方 RSS 订阅源。

- **文件位置**: `server_py/collectors/people_daily_collector.py`
- **RSS 源**:
    - 时政: `http://www.people.com.cn/rss/politics.xml`
    - 国际: `http://www.people.com.cn/rss/world.xml`
    - 金融: `http://www.people.com.cn/rss/finance.xml`
- **功能**:
    - `collect()` 方法：
        - 遍历 RSS URL 列表。
        - 使用 `httpx.get` 获取 XML 内容。
        - 解析 XML 提取 `item` 中的 `title`, `link`, `description`, `pubDate`。
        - 清洗 `description` 中的 HTML 标签。
        - 构造标准新闻对象：
            - `source`: 'PeopleDaily'
            - `type`: 'article'
            - `time`: 解析 `pubDate` 并格式化。
            - `id`: MD5(link) (使用链接作为唯一标识，防止重复)
- **依赖**: `httpx`, `xml.etree.ElementTree`, `hashlib`, `datetime`.

## 3. 集成到数据摄取服务

更新 `server_py/services/ingestion.py` 以启用新采集器。

- **步骤**:
    - 导入 `CCTVCollector` 和 `PeopleDailyCollector`。
    - 在 `start_ingestion_scheduler` 中实例化这两个采集器。
    - 添加调度任务：
        - `CCTVCollector`: 每 60 分钟运行一次 (id='cctv_ingestion')。
        - `PeopleDailyCollector`: 每 30 分钟运行一次 (id='peopledaily_ingestion')。
    - 在 `delayed_start` 中添加初始运行调用。

## 4. 验证

- 运行 `ingestion.py` 或重启后端服务。
- 检查日志输出，确认是否成功抓取数据。
- 检查数据库或前端页面，确认是否有来源为 'CCTV' 和 'PeopleDaily' 的新闻。
