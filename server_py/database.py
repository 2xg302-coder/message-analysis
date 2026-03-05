import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            content TEXT,
            time TEXT,
            timestamp TEXT,
            scraped_at TEXT,
            created_at TEXT,
            source TEXT,
            raw_data TEXT,
            analysis TEXT,
            analyzed_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_news(news_item: Dict[str, Any]) -> bool:
    if not news_item or 'id' not in news_item:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id FROM news WHERE id = ?', (news_item['id'],))
        if cursor.fetchone():
            return False
        
        record = news_item.copy()
        record['created_at'] = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO news (id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('id'),
            record.get('title', ''),
            record.get('link', ''),
            record.get('content', ''),
            record.get('time', ''),
            record.get('timestamp', ''),
            record.get('scrapedAt', ''),
            record['created_at'],
            record.get('source', 'unknown'),
            json.dumps(record)
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding news: {e}")
        return False
    finally:
        conn.close()

def add_news_batch(news_list: List[Dict[str, Any]]) -> int:
    if not news_list:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    added_count = 0
    
    try:
        for news_item in news_list:
            if not news_item or 'id' not in news_item:
                continue
            
            cursor.execute('SELECT id FROM news WHERE id = ?', (news_item['id'],))
            if cursor.fetchone():
                continue
            
            record = news_item.copy()
            record['created_at'] = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO news (id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('id'),
                record.get('title', ''),
                record.get('link', ''),
                record.get('content', ''),
                record.get('time', ''),
                record.get('timestamp', ''),
                record.get('scrapedAt', ''),
                record['created_at'],
                record.get('source', 'unknown'),
                json.dumps(record)
            ))
            added_count += 1
        
        conn.commit()
        return added_count
    except Exception as e:
        print(f"Error in batch add: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def get_latest_news(limit: int = 1000) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM news ORDER BY created_at DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                raw_data = json.loads(item['raw_data']) if item['raw_data'] else {}
                analysis = json.loads(item['analysis']) if item['analysis'] else None
                item.update(raw_data)
                item['analysis'] = analysis
                result.append(item)
            except:
                result.append(item)
        return result
    finally:
        conn.close()

def get_unanalyzed_news(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM news WHERE analysis IS NULL ORDER BY created_at ASC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                raw_data = json.loads(item['raw_data']) if item['raw_data'] else {}
                item.update(raw_data)
                result.append(item)
            except:
                result.append(item)
        return result
    finally:
        conn.close()

def save_analysis(news_id: str, analysis_result: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE news SET analysis = ?, analyzed_at = ? WHERE id = ?', 
                      (json.dumps(analysis_result), datetime.now().isoformat(), news_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return False
    finally:
        conn.close()

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) as count FROM news')
        total = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM news WHERE analysis IS NOT NULL')
        analyzed = cursor.fetchone()['count']
        
        pending = total - analyzed
        
        # Analyze last 1000 for details
        cursor.execute('SELECT analysis FROM news WHERE analysis IS NOT NULL ORDER BY created_at DESC LIMIT 1000')
        rows = cursor.fetchall()
        
        high_score_count = 0
        series_set = set()
        
        for row in rows:
            try:
                analysis = json.loads(row['analysis'])
                score = analysis.get('score', analysis.get('relevance_score', 0))
                if score >= 7:
                    high_score_count += 1
                if analysis.get('event_tag'):
                    series_set.add(analysis['event_tag'])
            except:
                pass
        
        # Trends (simplified)
        cursor.execute('''
            SELECT substr(created_at, 12, 2) as hour, count(*) as count 
            FROM news 
            GROUP BY hour 
            ORDER BY hour DESC 
            LIMIT 12
        ''')
        trends = [dict(row) for row in cursor.fetchall()]
        trends.reverse()
        
        return {
            'total': total,
            'analyzed': analyzed,
            'pending': pending,
            'high_score': high_score_count,
            'active_series': len(series_set),
            'trends': trends
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {'total': 0, 'analyzed': 0, 'pending': 0, 'trends': []}
    finally:
        conn.close()

def get_series_list() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT analysis, created_at FROM news WHERE analysis IS NOT NULL AND analysis LIKE '%\"event_tag\"%' ORDER BY created_at DESC LIMIT 2000")
        rows = cursor.fetchall()
        
        series_map = {}
        
        for row in rows:
            try:
                analysis = json.loads(row['analysis'])
                tag = analysis.get('event_tag')
                if tag:
                    if tag not in series_map:
                        series_map[tag] = {
                            'tag': tag,
                            'count': 0,
                            'latest_date': row['created_at'],
                            'sample_summary': analysis.get('summary')
                        }
                    series_map[tag]['count'] += 1
            except:
                pass
        
        # Sort by latest date desc
        return sorted(series_map.values(), key=lambda x: x['latest_date'], reverse=True)
    except Exception as e:
        print(f"Error getting series list: {e}")
        return []
    finally:
        conn.close()

def get_news_by_series(tag: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Use LIKE for broad match, then filter in python
        cursor.execute("SELECT * FROM news WHERE analysis LIKE ? ORDER BY created_at DESC", (f'%{tag}%',))
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            try:
                item = dict(row)
                raw_data = json.loads(item['raw_data']) if item['raw_data'] else {}
                analysis = json.loads(item['analysis']) if item['analysis'] else None
                
                if analysis and analysis.get('event_tag') == tag:
                    item.update(raw_data)
                    item['analysis'] = analysis
                    result.append(item)
            except:
                pass
        return result
    except Exception as e:
        print(f"Error getting news by series: {e}")
        return []
    finally:
        conn.close()

# Initialize on import if needed, but better to call explicitly
# init_db()
