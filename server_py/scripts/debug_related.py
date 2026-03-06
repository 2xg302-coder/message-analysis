
import asyncio
import sys
import os

# Add project root to path
sys.path.append("/home/aaa/projects/message-analysis/server_py")

from services.news_service import NewsService
from core.database import db

async def test_related():
    service = NewsService()
    tag = "俄乌冲突"
    print(f"Testing related series for tag: {tag}")
    
    try:
        # Mock DB execution if needed, or rely on actual DB if available
        # Assuming we can connect to the DB.
        
        # Test get_news_by_series
        print("1. Testing get_news_by_series...")
        news = await service.get_news_by_series(tag)
        print(f"Found {len(news)} news items")
        
        # Test get_series_list
        print("2. Testing get_series_list...")
        series = await service.get_series_list()
        print(f"Found {len(series)} series")
        
        # Test get_related_series
        print("3. Testing get_related_series...")
        related = await service.get_related_series(tag)
        print(f"Found {len(related)} related series")
        print(related)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_related())
