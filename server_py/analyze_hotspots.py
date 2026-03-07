
import asyncio
from sqlmodel import select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from models_orm import Series, Storyline
from core.database_orm import engine

async def analyze_series_hotspots():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Get all Series
        stmt = select(Series)
        result = await session.execute(stmt)
        series_list = result.scalars().all()
        
        series_stats = []
        
        for series in series_list:
            # 2. Count storylines for each series
            count_stmt = select(func.count(Storyline.id)).where(Storyline.series_id == series.id)
            count_result = await session.execute(count_stmt)
            count = count_result.scalar() or 0
            
            # 3. Sum importance
            imp_stmt = select(func.sum(Storyline.importance)).where(Storyline.series_id == series.id)
            imp_result = await session.execute(imp_stmt)
            total_importance = imp_result.scalar() or 0
            
            series_stats.append({
                "id": series.id,
                "title": series.title,
                "count": count,
                "total_importance": total_importance,
                "updated_at": series.updated_at
            })
            
        # 4. Sort by total_importance desc, then count desc
        # Sort logic: primary key is total_importance (cumulative impact), secondary is count (frequency)
        series_stats.sort(key=lambda x: (x['total_importance'], x['count']), reverse=True)
        
        # 5. Print Top 20 in a user-friendly format
        print("\n=== 事件连续剧热点追踪 Top 20 ===")
        print(f"{'排名':<6} {'主题 (Series)':<30} {'热度分 (Total Imp)':<18} {'事件数 (Storylines)':<18} {'最近更新'}")
        print("-" * 100)
        
        for i, item in enumerate(series_stats[:20], 1):
            updated_at = item['updated_at'].split('T')[0] if item['updated_at'] else 'N/A'
            print(f"{i:<6} {item['title']:<32} {item['total_importance']:<20} {item['count']:<20} {updated_at}")

if __name__ == "__main__":
    asyncio.run(analyze_series_hotspots())
