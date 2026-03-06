import json
import os
import sys
import re
from datetime import datetime
from typing import List, Dict, Any
from core.database import db

try:
    import asyncio
except Exception:
    asyncio = None

# Fix for Windows asyncio loop policy
if sys.platform == 'win32' and asyncio is not None:
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
        
        # DB is initialized globally in core/database.py

    async def collect(self, date_str: str = None) -> List[Dict[str, Any]]:
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
        source_errors = []
        try:
            # Import akshare here to avoid global event loop issues on Windows
            import akshare as ak

            # Try Baidu first
            try:
                if hasattr(ak, 'news_economic_baidu'):
                    df_baidu = await asyncio.to_thread(ak.news_economic_baidu, date=date_str)
                    events = self._process_df(df_baidu, "Baidu")
            except Exception as e:
                source_errors.append(f"Baidu: {e}")
                print(f"Baidu source failed: {e}")

            # Try Jin10 if Baidu failed or returned no events
            if not events:
                try:
                    if hasattr(ak, 'news_economic_jin10'):
                        df_jin10 = await asyncio.to_thread(ak.news_economic_jin10, date=date_str)
                        events = self._process_df(df_jin10, "Jin10")
                except Exception as e:
                    source_errors.append(f"Jin10: {e}")
                    print(f"Jin10 source failed: {e}")

            # Try Sina as last resort
            if not events:
                try:
                    if hasattr(ak, 'news_economic_sina'):
                        df_sina = await asyncio.to_thread(ak.news_economic_sina, date=date_str)
                        events = self._process_df(df_sina, "Sina")
                except Exception as e:
                    source_errors.append(f"Sina: {e}")
                    print(f"Sina source failed: {e}")

            if not events and source_errors:
                raise RuntimeError(f"Calendar sources unavailable for {date_str}: {' | '.join(source_errors)}")
        except Exception as e:
            message = str(e)
            if "No module named 'akshare'" in message:
                raise RuntimeError("未安装 akshare 依赖，请先执行: pip install akshare") from e
            raise RuntimeError(f"财经日历采集失败: {message}") from e
            
        # Save to DB
        await self.save_events_to_db(date_str, events)
        
        # Save to file (Backup)
        self.save_events(date_str, events)
        
        print(f"Collected {len(events)} high-importance events.")
        return events

    def _get_value(self, row: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
        for key in keys:
            if key in row and row.get(key) is not None:
                value = row.get(key)
                if str(value).strip() != "":
                    return value
        return default

    def _parse_importance(self, raw_value: Any) -> int:
        if raw_value is None:
            return 0
        if isinstance(raw_value, (int, float)):
            return int(raw_value)
        text = str(raw_value).strip()
        if not text:
            return 0
        
        # Stars
        stars = text.count('★') + text.count('⭐')
        if stars:
            return stars
            
        # Chinese
        if '高' in text:
            return 3
        if '中' in text:
            return 2
        if '低' in text:
            return 1
            
        # English
        text_lower = text.lower()
        if 'high' in text_lower:
            return 3
        if 'med' in text_lower or 'mid' in text_lower:
            return 2
        if 'low' in text_lower:
            return 1
            
        # Numbers
        match = re.search(r"\d+", text)
        if match:
            return int(match.group())
            
        return 0

    def _process_df(self, df, source_name: str) -> List[Dict[str, Any]]:
        source_events = []
        try:
            if df is None:
                return source_events
            
            # Check if df has 'empty' attribute (simple DataFrame check)
            if not hasattr(df, 'empty'):
                print(f"Warning: {source_name} returned non-DataFrame object: {type(df)}")
                return source_events

            if df.empty:
                return source_events

            print(f"Fetched {len(df)} raw events from {source_name}.")
            
            # DEBUG: Print columns and first row to debug importance issue
            print(f"DEBUG: {source_name} columns: {df.columns.tolist()}")
            if len(df) > 0:
                first_row = df.iloc[0].to_dict() if hasattr(df.iloc[0], "to_dict") else dict(df.iloc[0])
                print(f"DEBUG: First row sample: {first_row}")
            
            # Check if iterrows exists
            if not hasattr(df, 'iterrows'):
                print(f"Warning: {source_name} DataFrame missing iterrows: {type(df)}")
                return source_events

            skipped_count = 0
            for _, row in df.iterrows():
                try:
                    row_dict = row.to_dict() if hasattr(row, "to_dict") else dict(row)
                    
                    # Try more keys for importance
                    importance_val = self._get_value(row_dict, ['重要性', '重要程度', 'importance', 'star', 'stars', 'level', 'grade', 'rank'], 0)
                    importance = self._parse_importance(importance_val)
                    
                    # if importance < 3:
                    #     if skipped_count < 3: # Log first few skipped reasons
                    #         print(f"DEBUG: Skipped event due to low importance ({importance}): {row_dict.get('事件', row_dict.get('event', 'Unknown'))} [Raw importance: {importance_val}]")
                    #     skipped_count += 1
                    #     continue
                        
                    source_events.append({
                        "time": str(self._get_value(row_dict, ['时间', 'time', '日期时间'], '')),
                        "country": str(self._get_value(row_dict, ['地区', '国家', 'country'], '')),
                        "event": str(self._get_value(row_dict, ['事件', '指标', 'event', 'title'], '')),
                        "importance": importance,
                        "previous": str(self._get_value(row_dict, ['前值', '前值(修正前)', 'previous'], '')),
                        "consensus": str(self._get_value(row_dict, ['预期', '预测值', 'consensus', 'forecast'], '')),
                        "actual": str(self._get_value(row_dict, ['公布', '今值', 'actual'], ''))
                    })
                except Exception as e:
                    print(f"Error processing row from {source_name}: {e}")
                    continue
            
            if skipped_count > 0:
                print(f"DEBUG: Total skipped {skipped_count} low-importance events from {source_name}")
                
        except Exception as e:
            print(f"Error in _process_df for {source_name}: {e}")
            import traceback
            traceback.print_exc()

        return source_events

    async def save_events_to_db(self, date_str: str, events: List[Dict[str, Any]]):
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
                if await db.execute_update(query, params):
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
    import asyncio
    c = CalendarCollector(data_dir="../../server_py/data") # Adjust path for testing
    asyncio.run(c.collect())
