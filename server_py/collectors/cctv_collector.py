import akshare as ak
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any

class CCTVCollector:
    def __init__(self):
        self.source = 'CCTV'

    def generate_id(self, content: str, time_str: str) -> str:
        """Generate a unique ID based on content and time"""
        raw = f"{content}-{time_str}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def collect(self) -> List[Dict[str, Any]]:
        news_list = []
        
        # Collect for today and yesterday to ensure coverage
        dates_to_check = [
            datetime.now().strftime('%Y%m%d'),
            (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        ]

        for date_str in dates_to_check:
            try:
                # ak.news_cctv(date="YYYYMMDD")
                # Columns: date, title, content
                cctv_df = ak.news_cctv(date=date_str)
                
                if cctv_df is not None and not cctv_df.empty:
                    for _, row in cctv_df.iterrows():
                        title = row.get('title', '')
                        content = row.get('content', '')
                        
                        if not content: continue
                        if not title: title = content[:50] + "..."
                        
                        # News is usually broadcast at 19:00
                        # Convert YYYYMMDD to YYYY-MM-DD
                        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                        full_time = f"{date_formatted} 19:00:00"
                            
                        news_item = {
                            'id': self.generate_id(content, full_time),
                            'title': title,
                            'content': content,
                            'link': '', # No direct link provided by akshare, maybe construct one if possible
                            'time': full_time,
                            'source': 'CCTV',
                            'type': 'article',
                            'scrapedAt': datetime.now().isoformat(),
                            'raw_tags': '新闻联播'
                        }
                        news_list.append(news_item)
            except Exception as e:
                # It's normal to fail if data is not yet available for today
                # print(f"Info: No CCTV news for {date_str} or error: {e}")
                pass
            
        if not news_list:
            pass
            # print(f"No CCTV news fetched.")
            
        return news_list
