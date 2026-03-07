import akshare as ak
import hashlib
from datetime import datetime
from typing import List, Dict, Any

class EastMoneyCollector:
    def __init__(self):
        self.source = 'EastMoney'

    def generate_id(self, link: str, title: str) -> str:
        """Generate a unique ID based on link or title"""
        raw = f"{link}-{title}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def collect(self) -> List[Dict[str, Any]]:
        # print(f"🚀 Starting {self.source} news collection...")
        try:
            # Use ak.stock_news_em_general() for general news
            news_df = ak.stock_news_em_general()
            
            if news_df.empty:
                print(f"⚠️ No news fetched from {self.source}.")
                return []
                
            news_list = []
            
            for _, row in news_df.iterrows():
                title = row.get('新闻标题', '')
                content = row.get('新闻内容', '')
                time_str = row.get('发布时间', '')
                link = row.get('文章链接', '')
                
                if not title:
                    continue
                    
                news_item = {
                    'id': self.generate_id(link, title),
                    'title': title,
                    'content': content or title, # Fallback to title if content is empty
                    'link': link,
                    'time': time_str,
                    'source': self.source,
                    'type': 'article',
                    'scrapedAt': datetime.now().isoformat()
                }
                news_list.append(news_item)
                
            # print(f"✅ {self.source} collection complete. Fetched {len(news_list)} items.")
            return news_list
            
        except Exception as e:
            print(f"❌ Error fetching news from {self.source}: {e}")
            return []
