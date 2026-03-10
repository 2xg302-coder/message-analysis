from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from core.database import db
from core.logging import get_logger

logger = get_logger("maintenance_service")

class MaintenanceService:
    def __init__(self, database=None):
        self.db = database or db

    async def get_db_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            stats = {}
            
            # 1. 总数据量
            total_res = await self.db.execute_query("SELECT COUNT(*) as count FROM news")
            stats['total_news'] = total_res[0]['count'] if total_res else 0
            
            # 2. 按来源统计
            source_res = await self.db.execute_query("SELECT source, COUNT(*) as count FROM news GROUP BY source")
            stats['by_source'] = {row['source']: row['count'] for row in source_res}
            
            # 3. 按分数统计 (分段)
            score_res = await self.db.execute_query("""
                SELECT 
                    CASE 
                        WHEN impact_score >= 7 THEN 'high'
                        WHEN impact_score >= 4 THEN 'medium'
                        WHEN impact_score >= 1 THEN 'low'
                        ELSE 'unanalyzed'
                    END as category,
                    COUNT(*) as count
                FROM news
                GROUP BY category
            """)
            stats['by_score'] = {row['category']: row['count'] for row in score_res}
            
            # 4. 最早/最新时间
            time_res = await self.db.execute_query("SELECT MIN(created_at) as min_time, MAX(created_at) as max_time FROM news")
            if time_res:
                stats['time_range'] = {
                    'earliest': time_res[0]['min_time'],
                    'latest': time_res[0]['max_time']
                }
                
            # 5. 数据库文件大小 (估算，SQLite 页面大小通常为 4KB)
            # 这里无法直接获取文件大小，除非使用 os.stat。但在 service 层最好只操作 DB。
            # 可以通过 page_count * page_size 获取
            try:
                page_count_res = await self.db.execute_query("PRAGMA page_count")
                page_size_res = await self.db.execute_query("PRAGMA page_size")
                if page_count_res and page_size_res:
                    size_bytes = page_count_res[0]['page_count'] * page_size_res[0]['page_size']
                    stats['db_size_mb'] = round(size_bytes / (1024 * 1024), 2)
            except Exception:
                stats['db_size_mb'] = 0
                
            return stats
        except Exception as e:
            logger.error(f"Error getting DB stats: {e}")
            return {}

    async def cleanup_news(self, 
                         days_retention: int = 30, 
                         min_score: int = 0, 
                         target_source: Optional[str] = None,
                         dry_run: bool = False) -> Dict[str, Any]:
        """
        清理新闻数据
        :param days_retention: 保留最近多少天的数据 (删除 created_at < N天前)
        :param min_score: 仅删除分数低于此值的数据 (默认 0，即删除所有符合时间条件的数据)
        :param target_source: 仅删除特定来源的数据 (如 'ITHome')
        :param dry_run: 如果为 True，仅返回预计删除数量，不执行删除
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_retention)).isoformat()
            
            where_clauses = ["created_at < ?"]
            params = [cutoff_date]
            
            if min_score > 0:
                # 保护高分数据：只删除分数 < min_score 的
                # 注意：未分析的数据 (impact_score IS NULL) 通常也应该被视为低分处理，或者由另一个参数控制
                # 这里假设 impact_score 为 NULL 的视为 0
                where_clauses.append("(impact_score < ? OR impact_score IS NULL)")
                params.append(min_score)
                
            if target_source:
                where_clauses.append("source = ?")
                params.append(target_source)
                
            where_sql = " AND ".join(where_clauses)
            
            # 1. 统计数量
            count_query = f"SELECT COUNT(*) as count FROM news WHERE {where_sql}"
            count_res = await self.db.execute_query(count_query, tuple(params))
            count = count_res[0]['count'] if count_res else 0
            
            if dry_run or count == 0:
                return {
                    "deleted_count": 0,
                    "estimated_count": count,
                    "dry_run": True
                }
            
            # 2. 执行删除
            delete_query = f"DELETE FROM news WHERE {where_sql}"
            await self.db.execute_update(delete_query, tuple(params))
            
            # 3. (可选) VACUUM
            # await self.db.execute_update("VACUUM") 
            # VACUUM 比较耗时，建议单独触发
            
            return {
                "deleted_count": count,
                "estimated_count": count,
                "dry_run": False
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up news: {e}")
            return {"error": str(e)}

    async def delete_by_source(self, source: str) -> Dict[str, Any]:
        """直接删除指定来源的所有数据"""
        try:
            # 1. 统计
            count_res = await self.db.execute_query("SELECT COUNT(*) as count FROM news WHERE source = ?", (source,))
            count = count_res[0]['count'] if count_res else 0
            
            if count == 0:
                return {"deleted_count": 0, "source": source}
                
            # 2. 删除
            await self.db.execute_update("DELETE FROM news WHERE source = ?", (source,))
            
            return {"deleted_count": count, "source": source}
        except Exception as e:
            logger.error(f"Error deleting by source {source}: {e}")
            return {"error": str(e)}
            
    async def vacuum_db(self) -> bool:
        """执行 VACUUM 释放空间"""
        try:
            # execute_update 可能不支持 VACUUM (因为它是 DDL)，需要直接用 connection
            async with self.db.get_connection() as conn:
                await conn.execute("VACUUM")
            return True
        except Exception as e:
            logger.error(f"Error vacuuming DB: {e}")
            return False

maintenance_service = MaintenanceService()
