
import asyncio
import json
from sqlmodel import select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from models_orm import Storyline
from core.database_orm import engine

async def analyze_storyline_hotspots():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all active storylines
        stmt = select(Storyline).where(Storyline.status == 'active')
        result = await session.execute(stmt)
        storylines = result.scalars().all()
        
        storyline_stats = []
        
        for sl in storylines:
            # Calculate news count
            news_count = 0
            if sl.related_news_ids:
                try:
                    news_ids = json.loads(sl.related_news_ids)
                    news_count = len(news_ids)
                except:
                    pass
            
            storyline_stats.append({
                "id": sl.id,
                "title": sl.title,
                "series_title": sl.series_title or "N/A",
                "importance": sl.importance,
                "news_count": news_count,
                "date": sl.date
            })
            
        # Sort by importance desc, then news_count desc
        storyline_stats.sort(key=lambda x: (x['importance'], x['news_count']), reverse=True)
        
        print("\n=== 热门事件 (Storylines) Top 20 ===")
        print(f"{'排名':<6} {'事件标题 (Storyline)':<40} {'所属连续剧 (Series)':<20} {'重要性':<8} {'关联新闻数':<12} {'日期'}")
        print("-" * 110)
        
        for i, item in enumerate(storyline_stats[:20], 1):
            title = item['title'][:38] + ".." if len(item['title']) > 38 else item['title']
            series = item['series_title'][:18] + ".." if len(item['series_title']) > 18 else item['series_title']
            print(f"{i:<6} {title:<40} {series:<20} {item['importance']:<8} {item['news_count']:<12} {item['date']}")

if __name__ == "__main__":
    asyncio.run(analyze_storyline_hotspots())
