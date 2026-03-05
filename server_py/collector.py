import akshare as ak
import pandas as pd
import hashlib
import json
from datetime import datetime
from database import add_news_batch

def generate_id(link: str, title: str) -> str:
    """Generate a unique ID based on link or title"""
    raw = f"{link}-{title}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def fetch_and_save_news():
    print("🚀 Starting AkShare news collection...")
    try:
        # Fetch general stock news from East Money
        news_df = ak.stock_news_em_general()
        
        if news_df.empty:
            print("⚠️ No news fetched from AkShare.")
            return 0
            
        # Rename columns to match our schema
        # Expected columns: "新闻标题", "新闻内容", "发布时间", "文章链接"
        news_list = []
        
        for _, row in news_df.iterrows():
            title = row.get('新闻标题', '')
            content = row.get('新闻内容', '')
            time_str = row.get('发布时间', '')
            link = row.get('文章链接', '')
            
            if not title:
                continue
                
            news_item = {
                'id': generate_id(link, title),
                'title': title,
                'content': content or title, # Fallback to title if content is empty
                'link': link,
                'time': time_str,
                'source': 'EastMoney',
                'scrapedAt': datetime.now().isoformat()
            }
            news_list.append(news_item)
            
        # Batch insert into database
        count = add_news_batch(news_list)
        print(f"✅ AkShare collection complete. Added {count} new items.")
        return count
        
    except Exception as e:
        print(f"❌ Error fetching news from AkShare: {e}")
        return 0

if __name__ == "__main__":
    fetch_and_save_news()
