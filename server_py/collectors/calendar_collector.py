import json
import os
import sys
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.database import db

# Fix for Windows asyncio loop policy
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass

# Fix for proxy issues (unset proxy environment variables if they are causing issues)
# Or configure them correctly if needed.
# For now, let's try to clear them if they point to a local proxy that might be down (e.g. 7890)
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']

class CalendarCollector:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        # Keep file path for legacy/backup, but primary is DB
        self.file_path = os.path.join(self.data_dir, "expected_events.json")
        
        # Initialize DB schema if not already done (re-run init)
        db._init_db()

    def collect(self, date_str: str = None) -> List[Dict[str, Any]]:
        """
        Collect economic calendar data.
        :param date_str: Date string in 'YYYYMMDD' format. Defaults to today.
        """
        if not date_str:
            date_str = datetime.now().strftime('%Y%m%d')
        
        # Ensure we have a valid date string for akshare if possible
        # If input is YYYY-MM-DD, convert to YYYYMMDD
        if '-' in date_str:
             date_str = date_str.replace('-', '')
             
        print(f"Fetching economic calendar for {date_str}...")
        
        events = []
        try:
            # Import akshare here to avoid global event loop issues on Windows
            import akshare as ak
            
            # Helper to process dataframe from different sources
            def process_df(df, source_name):
                source_events = []
                if df is None or df.empty:
                    return source_events
                
                print(f"Fetched {len(df)} raw events from {source_name}.")
                for _, row in df.iterrows():
                    # Standardize importance (Baidu/Jin10 might have different columns)
                    importance = row.get('重要性', 0)
                    try:
                        # Ensure importance is integer
                        if isinstance(importance, str):
                            # Check for stars (e.g. "★★★") or numeric string
                            if '★' in importance:
                                importance = importance.count('★')
                            elif '高' in importance:
                                importance = 3
                            elif '中' in importance:
                                importance = 2
                            else:
                                importance = int(importance)
                        else:
                            importance = int(importance)
                    except:
                        importance = 0
                    
                    if importance >= 3:
                        source_events.append({
                            "time": str(row.get('时间', '')),
                            "country": str(row.get('地区', '')),
                            "event": str(row.get('事件', '')),
                            "importance": importance,
                            "previous": str(row.get('前值', '')),
                            "consensus": str(row.get('预期', '')),
                            "actual": str(row.get('公布', ''))
                        })
                return source_events

            # Try Baidu first
            try:
                if hasattr(ak, 'news_economic_baidu'):
                    df_baidu = ak.news_economic_baidu(date=date_str)
                    events = process_df(df_baidu, "Baidu")
            except Exception as e:
                print(f"Baidu source failed: {e}")

            # Try Jin10 if Baidu failed or returned no events
            if not events:
                try:
                    if hasattr(ak, 'news_economic_jin10'):
                        df_jin10 = ak.news_economic_jin10(date=date_str)
                        events = process_df(df_jin10, "Jin10")
                except Exception as e:
                    print(f"Jin10 source failed: {e}")

            # Try Sina as last resort
            if not events:
                try:
                    if hasattr(ak, 'news_economic_sina'):
                        df_sina = ak.news_economic_sina(date=date_str)
                        events = process_df(df_sina, "Sina")
                except Exception as e:
                    print(f"Sina source failed: {e}")

        except Exception as e:
            print(f"Global calendar fetch error: {e}")
            
        # Save to DB
        self.save_events_to_db(date_str, events)
        
        # Save to file (Backup)
        self.save_events(date_str, events)
        
        print(f"Collected {len(events)} high-importance events.")
        return events

    def save_events_to_db(self, date_str: str, events: List[Dict[str, Any]]):
        if not events:
            return
            
        # Standardize date to YYYY-MM-DD
        try:
            date_fmt = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except:
            date_fmt = date_str

        count = 0
        for event in events:
            try:
                # Upsert (using INSERT OR REPLACE or check existence)
                # Using INSERT OR IGNORE to avoid duplicates if UNIQUE constraint is hit
                # But we might want to update values like 'actual'.
                # Let's use REPLACE
                query = '''
                    INSERT OR REPLACE INTO calendar_events 
                    (date, time, country, event, importance, previous, consensus, actual)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (
                    date_fmt,
                    event.get('time', ''),
                    event.get('country', ''),
                    event.get('event', ''),
                    event.get('importance', 0),
                    event.get('previous', ''),
                    event.get('consensus', ''),
                    event.get('actual', '')
                )
                if db.execute_update(query, params):
                    count += 1
            except Exception as e:
                print(f"Error saving event to DB: {e}")
        
        print(f"Saved {count} events to database for {date_fmt}.")

    def save_events(self, date_str: str, events: List[Dict[str, Any]]):
        # Load existing
        data = {}
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {}
        
        # Update
        formatted_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        data[formatted_date] = events
        
        # Save
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_events(self, date_str: str = None) -> List[Dict[str, Any]]:
        """
        Get events for a specific date (YYYY-MM-DD).
        """
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(date_str, [])
            except:
                return []
        return []

if __name__ == "__main__":
    c = CalendarCollector(data_dir="../../server_py/data") # Adjust path for testing
    c.collect()
