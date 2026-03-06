# 后端重构与优化计划

## 1. 概述

本文档详细记录了 `server_py` 后端代码中发现的问题及其优化方案。目标是提升系统的性能、安全性和可维护性。

## 2. 核心问题分析

### 2.1 数据库与性能

* **批量写入效率低**: `add_news_batch` 目前采用循环单条插入的方式，导致大量数据库连接开销。

* **统计查询性能差**: `get_tag_stats` 等接口将所有数据拉取到内存中计算，随着数据量增长将不可用。

* **原生 SQL 风险**: 大量使用原生 SQL 字符串拼接，虽然部分使用了参数化，但动态查询构建逻辑脆弱且难以维护。

* **缺乏迁移管理**: 数据库表结构硬编码在初始化代码中，缺乏版本控制。

### 2.2 系统架构

* **全局单例模式**: `db` 和 `news_service` 作为全局变量使用，违反了 FastAPI 的依赖注入原则，不利于测试和模块解耦。

* **循环依赖**: 模块间存在循环导入风险，导致在函数内部进行 import。

* **错误处理**: 异常捕获过于宽泛，缺乏具体的错误类型处理。

### 2.3 安全性

* **API Key 验证**: 使用字符串直接比较，存在时序攻击风险。

* **输入校验**: 依赖 Pydantic 但在 SQL 层缺乏进一步的校验。

## 3. 优化方案与实施计划

### 阶段一：性能与安全修复 (立即执行)

1. **优化批量写入**: 重写 `NewsService.add_news_batch`，使用 `executemany` 或单次事务提交。
2. **修复 API Key 验证**: 在 `main.py` 中使用 `secrets.compare_digest` 进行常量时间比较。
3. **优化统计查询**: 重写 `get_tag_stats`，尝试使用 SQL 聚合或优化内存处理逻辑。

### 阶段二：架构重构 (建议)

1. **引入依赖注入**:

   * 创建 `get_db` 和 `get_news_service` 依赖项。

   * 重构 `routers` 使用 `Depends` 获取服务实例。
2. **规范化配置**: 统一使用 `config.py` 管理所有配置，包括日志和数据库路径。

### 阶段三：长期演进

1. **引入 ORM**: 迁移至 SQLAlchemy (Async) 或 SQLModel，彻底解决 SQL 拼接问题。
2. **数据库迁移**: 引入 Alembic 管理数据库版本。
3. **缓存层**: 为高频统计接口引入 Redis 缓存。

## 4. 代码变更示例

### 批量写入优化

```python
# Before
async def add_news_batch(self, news_list):
    for item in news_list:
        await self.add_news(item)

# After
async def add_news_batch(self, news_list):
    async with self.db.transaction():
        await self.db.executemany(sql, params_list)
```

### 安全验证优化

```python
# Before
if api_key != settings.API_SECRET: ...

# After
import secrets
if not secrets.compare_digest(api_key, settings.API_SECRET): ...
```

