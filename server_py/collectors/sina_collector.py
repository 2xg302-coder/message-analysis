import akshare as ak
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger("sina_collector")

class SinaCollector:
    def __init__(self):
        self.source = 'Sina/CLS'

    def generate_id(self, content: str, time_str: str) -> str:
        """Generate a unique ID based on content and time"""
        raw = f"{content}-{time_str}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _fetch_cls_df_with_fallback(self):
        """
        逐级尝试 CLS 数据接口，任一成功返回 DataFrame。
        优先顺序：
        1) stock_telegraph_cls
        2) stock_info_global_cls
        3) stock_zh_a_alert_cls
        """
        fallback_chain = [
            "stock_telegraph_cls",
            "stock_info_global_cls",
            "stock_zh_a_alert_cls",
        ]

        for fn_name in fallback_chain:
            if not hasattr(ak, fn_name):
                continue
            try:
                fn = getattr(ak, fn_name)
                df = fn()
                if df is not None:
                    logger.info(f"CLS fetch succeeded with {fn_name}, rows={len(df)}")
                    return df
            except Exception as e:
                logger.warning(f"CLS fetch failed with {fn_name}: {e}")

        return None

    def collect(self) -> List[Dict[str, Any]]:
        news_list = []
        
        # --- 1. Fetch CLS Data (Cailian She) ---
        try:
            cls_df = self._fetch_cls_df_with_fallback()
                
            if cls_df is not None and not cls_df.empty:
                for _, row in cls_df.iterrows():
                    title = row.get('标题', '')
                    content = row.get('内容', '')
                    time_str = row.get('发布时间', '')
                    
                    if not content: continue
                    if not title: title = content[:50] + "..."
                    
                    # Handle time format
                    if not isinstance(time_str, str): time_str = str(time_str)
                    if len(time_str) <= 8: # HH:MM:SS
                        today = datetime.now().strftime('%Y-%m-%d')
                        full_time = f"{today} {time_str}"
                    else:
                        full_time = time_str
                        
                    news_item = {
                        'id': self.generate_id(content, full_time),
                        'title': title,
                        'content': content,
                        'link': '',
                        'time': full_time,
                        'source': 'CLS', # Explicitly mark as CLS
                        'type': 'flash',
                        'scrapedAt': datetime.now().isoformat(),
                        'raw_tags': row.get('标签', '')
                    }
                    news_list.append(news_item)
        except Exception as e:
            print(f"Error fetching CLS news: {e}")

        # --- 2. Fetch Sina Data (Sina 7x24) ---
        try:
            sina_df = None
            if hasattr(ak, 'stock_info_global_sina'):
                sina_df = ak.stock_info_global_sina()
                
            if sina_df is not None and not sina_df.empty:
                for _, row in sina_df.iterrows():
                    # Sina usually has columns: ['时间', '内容']
                    content = row.get('内容', '')
                    time_str = row.get('时间', '')
                    
                    if not content: continue
                    title = content[:50] + "..."
                    
                    # Handle time format
                    if not isinstance(time_str, str): time_str = str(time_str)
                    # Sina time is usually full datetime 'YYYY-MM-DD HH:MM:SS'
                    full_time = time_str
                        
                    news_item = {
                        'id': self.generate_id(content, full_time),
                        'title': title,
                        'content': content,
                        'link': '',
                        'time': full_time,
                        'source': 'Sina', # Explicitly mark as Sina
                        'type': 'flash',
                        'scrapedAt': datetime.now().isoformat(),
                        'raw_tags': '' # Sina usually doesn't provide tags here
                    }
                    news_list.append(news_item)
        except Exception as e:
            print(f"Error fetching Sina news: {e}")
            
        if not news_list:
            print(f"No news fetched from Sina or CLS.")
            
        return news_list
