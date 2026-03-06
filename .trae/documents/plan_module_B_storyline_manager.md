# 模块 B: 主线标签管理与归档 (Storyline Manager)

## 1. 目标
负责主线标签的生命周期管理，包括存储、激活、查询和每日归档。此模块是主线追踪的核心数据管理层。

## 2. 独立性说明
- **输入**：模块 A 生成的 JSON 主线列表。
- **输出**：持久化的 Storyline 记录，供其他模块调用。
- **依赖**：SQLite 数据库，API 层（FastAPI）。

## 3. 实现步骤

### 3.1 数据库模式设计 (`server_py/models_orm.py`)
- 新增 `Storyline` 表结构：
    - `id` (PK): 唯一标识符（UUID 或自增）。
    - `date`: 日期（YYYY-MM-DD）。
    - `title`: 主线标题（如"美国非农数据"）。
    - `keywords`: 关键词列表（JSON）。
    - `description`: 描述。
    - `importance`: 重要性 (1-5)。
    - `status`: 'active' (活跃), 'archived' (归档)。
    - `embedding`: 向量数据（可选，或存向量库）。
    - `created_at`: 创建时间。
    - `updated_at`: 更新时间。
- 执行 Alembic 迁移或手动创建表。

### 3.2 业务逻辑实现 (`server_py/services/storyline_manager.py`)
- **创建主线**：`create_storyline(storyline_data)`，支持去重。
- **激活主线**：`activate_storyline(storyline_id)`。
- **归档主线**：`archive_storylines(date)`，将指定日期的活跃主线状态改为 archived。
- **查询主线**：`get_active_storylines()`，返回当前活跃主线列表。

### 3.3 API 接口开发 (`server_py/routers/storyline.py`)
- `POST /api/storylines`：手动创建主线。
- `GET /api/storylines/active`：获取当前活跃主线（供前端展示和模块 C 调用）。
- `GET /api/storylines/history`：查询历史归档主线。
- `PUT /api/storylines/{id}/archive`：手动归档。

## 4. 测试计划
- 编写 CRUD 测试 `tests/test_storyline_manager.py`。
- 验证主线状态转换逻辑。
