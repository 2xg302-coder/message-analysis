import akshare as ak
import hashlib
from datetime import datetime
from typing import List, Dict, Any

class SinaCollector:
    def __init__(self):
        self.source = 'Sina/CLS'

    def generate_id(self, content: str, time_str: str) -> str:
        """Generate a unique ID based on content and time"""
        raw = f"{content}-{time_str}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def collect(self) -> List[Dict[str, Any]]:
        print(f"🚀 Starting {self.source} news collection...")
        try:
            # Use ak.stock_telegraph_cls() for flash news
            # Columns: 标题, 内容, 发布时间, 标签
            news_df = ak.stock_telegraph_cls()
            
            if news_df.empty:
                print(f"⚠️ No news fetched from {self.source}.")
                return []
                
            news_list = []
            
            for _, row in news_df.iterrows():
                title = row.get('标题', '')
                content = row.get('内容', '')
                time_str = row.get('发布时间', '')
                # Tags might be available depending on the API response structure
                # Ensure we handle different possible column names or missing columns
                
                if not content:
                    continue
                    
                # For flash news, title might be empty or same as content
                if not title:
                    title = content[:50] + "..."
                
                # Combine date with time if time_str is just time
                # Usually stock_telegraph_cls returns full date or just time. 
                # We'll assume it returns something usable or we might need to fix it.
                # If it's just HH:MM:SS, append today's date.
                if len(time_str) <= 8: # HH:MM:SS
                    today = datetime.now().strftime('%Y-%m-%d')
                    full_time = f"{today} {time_str}"
                else:
                    full_time = time_str

                news_item = {
                    'id': self.generate_id(content, full_time),
                    'title': title,
                    'content': content,
                    'link': '', # Flash news often has no link
                    'time': full_time,
                    'source': self.source,
                    'type': 'flash',
                    'scrapedAt': datetime.now().isoformat(),
                    'raw_tags': row.get('标签', '') # specific to CLS
                }
                news_list.append(news_item)
                
            print(f"✅ {self.source} collection complete. Fetched {len(news_list)} items.")
            return news_list
            
        except Exception as e:
            print(f"❌ Error fetching news from {self.source}: {e}")
            return []
