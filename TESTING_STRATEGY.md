# 测试策略文档 (Testing Strategy)

## 1. 测试目标 (Objectives)
构建全方位的质量保障体系，重点确保：
- **数据采集稳定性**：确保从 Sina, EastMoney, AKShare 等多源异构数据的解析准确性和容错性。
- **核心业务逻辑正确性**：验证 SimHash 去重、FlashText 关键词提取、情感分析等核心算法。
- **API 接口可靠性**：保证 RESTful API 的契约一致性、响应速度和错误处理机制。
- **前端交互流畅性**：确保 React 组件在不同数据状态下的渲染正确性。

## 2. 测试分层 (Test Pyramid)

### 2.1 后端测试 (Backend Testing) - 优先级：高
采用 `pytest` 作为主要测试框架，配合 `httpx` 进行异步 API 测试。

- **单元测试 (Unit Tests)**:
  - **Collectors**: 针对 `sina_collector.py`, `eastmoney_collector.py`, `calendar_collector.py` 编写测试。
    - *重点*: 模拟 (Mock) HTML/JSON 响应，验证解析逻辑，特别是针对脏数据和缺字段的容错处理（如 AKShare 的 `importance` 字段）。
  - **Services**: 测试 `Ingestion` 服务的 SimHash 去重逻辑和 `Processor` 的规则评级。
  - **Utils**: 测试日期处理、字符串清洗等工具函数。

- **接口/集成测试 (Integration/API Tests)**:
  - **Routers**: 测试 `/news`, `/calendar`, `/analysis` 等端点。
    - 验证 HTTP 状态码 (200, 400, 404, 500)。
    - 验证响应 Payload 结构符合 Pydantic 模型。
    - 验证分页、筛选、排序参数的有效性。
  - **Database**: 验证 CRUD 操作和事务一致性（使用测试数据库 `test.db`）。

### 2.2 前端测试 (Frontend Testing) - 优先级：中
采用 `Vitest` (与 Vite 原生集成) + `React Testing Library`。

- **组件测试 (Component Tests)**:
  - 验证 `NewsCard`、`CalendarView` 等核心组件的渲染。
  - 测试用户交互（如点击筛选、切换 Tab）。
- **工具测试**:
  - 验证前端的数据格式化函数（如 `dayjs` 封装）。

### 2.3 性能与负载测试 (Performance & Load Testing) - 优先级：低（后续阶段）
- 使用 `Locust` 或 Python 脚本模拟高并发数据采集和 API 请求。
- 监控 SQLite 在大数据量下的查询性能，评估是否需要迁移至 PostgreSQL。

## 3. 实施计划 (Implementation Roadmap)

### 阶段一：后端基础设施 (当前重点)
1.  安装测试依赖：`pytest`, `pytest-asyncio`, `httpx`, `pytest-cov`。
2.  配置 `pytest.ini` 和测试目录结构 (`server_py/tests/`)。
3.  编写核心 Collector 的解析测试用例（覆盖 Core Memory 中提到的解析容错问题）。
4.  编写基础 API 的冒烟测试。

### 阶段二：前端测试环境
1.  配置 Vitest 环境。
2.  为关键业务组件添加快照测试 (Snapshot Testing)。

### 阶段三：CI/CD 集成
1.  配置 GitHub Actions / Gitee Go，在提交代码时自动运行测试。

## 4. 关键测试场景 (Critical Test Scenarios)
- **场景 A (财经日历)**: 模拟 AKShare 返回包含中文/英文不同格式的 `importance` 字段，验证解析器是否能正确归一化。
- **场景 B (新闻去重)**: 模拟两条文本相似度极高的新闻，验证 SimHash 是否能正确识别并去重。
- **场景 C (API 健壮性)**: 发送非法参数（如错误的日期格式、负数分页），验证 API 是否返回标准的 HTTP 422/400 错误而非 500 崩溃。
