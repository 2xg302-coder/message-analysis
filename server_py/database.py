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

def migrate_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(news)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        new_columns = {
            'type': "TEXT DEFAULT 'article'",
            'tags': "TEXT",
            'entities': "TEXT",
            'impact_score': "INTEGER",
            'sentiment_score': "REAL",
            'simhash': "TEXT"
        }
        
        for col, defn in new_columns.items():
            if col not in columns:
                print(f"Adding column {col} to news table...")
                try:
                    cursor.execute(f"ALTER TABLE news ADD COLUMN {col} {defn}")
                except Exception as e:
                    print(f"Error adding column {col}: {e}")
        
        conn.commit()
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()

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
            analyzed_at TEXT,
            type TEXT DEFAULT 'article',
            tags TEXT,
            entities TEXT,
            impact_score INTEGER,
            sentiment_score REAL,
            simhash TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            keyword TEXT PRIMARY KEY,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    migrate_db()

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
        
        # Handle complex types for new columns
        tags = json.dumps(record.get('tags', [])) if isinstance(record.get('tags'), list) else record.get('tags')
        entities = json.dumps(record.get('entities', {})) if isinstance(record.get('entities'), dict) else record.get('entities')
        
        cursor.execute('''
            INSERT INTO news (
                id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data,
                type, tags, entities, impact_score, sentiment_score, simhash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(record),
            record.get('type', 'article'),
            tags,
            entities,
            record.get('impact_score', 0),
            record.get('sentiment_score', 0.0),
            record.get('simhash')
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
            
            tags = json.dumps(record.get('tags', [])) if isinstance(record.get('tags'), list) else record.get('tags')
            entities = json.dumps(record.get('entities', {})) if isinstance(record.get('entities'), dict) else record.get('entities')
            
            cursor.execute('''
                INSERT INTO news (
                    id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data,
                    type, tags, entities, impact_score, sentiment_score, simhash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(record),
                record.get('type', 'article'),
                tags,
                entities,
                record.get('impact_score', 0),
                record.get('sentiment_score', 0.0),
                record.get('simhash')
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
                # Parse JSON fields
                if item.get('raw_data'):
                    raw_data = json.loads(item['raw_data'])
                    item.update(raw_data) # Be careful not to overwrite new columns if raw_data has old values
                
                if item.get('analysis'):
                    item['analysis'] = json.loads(item['analysis'])
                
                if item.get('tags'):
                    item['tags'] = json.loads(item['tags'])
                
                if item.get('entities'):
                    item['entities'] = json.loads(item['entities'])
                    
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
                if item.get('raw_data'):
                    item.update(json.loads(item['raw_data']))
                if item.get('tags'):
                    item['tags'] = json.loads(item['tags'])
                if item.get('entities'):
                    item['entities'] = json.loads(item['entities'])
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
        cursor.execute('SELECT analysis, impact_score FROM news WHERE analysis IS NOT NULL ORDER BY created_at DESC LIMIT 1000')
        rows = cursor.fetchall()
        
        high_score_count = 0
        medium_score_count = 0
        low_score_count = 0
        series_set = set()
        
        for row in rows:
            try:
                # Use impact_score column if available and non-zero, otherwise fallback to analysis
                impact = row['impact_score']
                if not impact and row['analysis']:
                    analysis = json.loads(row['analysis'])
                    impact = analysis.get('score', analysis.get('relevance_score', 0))
                
                if impact:
                    if impact >= 4: # Assuming 1-5 scale, 4-5 is high? Or user said 1-5.
                        # Old logic: score >= 7 (high), >= 4 (medium). 
                        # New impact_score is 1-5. Let's say 4-5 is high, 3 medium, 1-2 low.
                        # Wait, user didn't define thresholds. I'll stick to old logic if using old score, 
                        # but for new impact_score (1-5), maybe 5 is high, 3-4 medium?
                        # Let's just use the value directly if it's new data.
                        if impact >= 4:
                            high_score_count += 1
                        elif impact >= 2:
                            medium_score_count += 1
                        else:
                            low_score_count += 1
                
                if row['analysis']:
                    analysis = json.loads(row['analysis'])
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
            'medium_score': medium_score_count,
            'low_score': low_score_count,
            'active_series': len(series_set),
            'trends': trends
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {'total': 0, 'analyzed': 0, 'pending': 0, 'trends': []}
    finally:
        conn.close()

def get_watchlist() -> List[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT keyword FROM watchlist ORDER BY created_at ASC')
        rows = cursor.fetchall()
        return [row['keyword'] for row in rows]
    except Exception as e:
        print(f"Error getting watchlist: {e}")
        return []
    finally:
        conn.close()

def update_watchlist(keywords: List[str]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Full replace strategy
        cursor.execute('DELETE FROM watchlist')
        current_time = datetime.now().isoformat()
        for kw in keywords:
            cursor.execute('INSERT INTO watchlist (keyword, created_at) VALUES (?, ?)', 
                          (kw, current_time))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating watchlist: {e}")
        conn.rollback()
        return False
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
                if item.get('raw_data'):
                    item.update(json.loads(item['raw_data']))
                
                analysis = json.loads(item['analysis']) if item['analysis'] else None
                
                if analysis and analysis.get('event_tag') == tag:
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

def get_news_filtered(limit: int = 100, offset: int = 0, news_type: Optional[str] = None, min_impact: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM news WHERE 1=1"
    params = []
    
    if news_type:
        query += " AND type = ?"
        params.append(news_type)
        
    if min_impact:
        query += " AND impact_score >= ?"
        params.append(min_impact)
        
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.append(limit)
    params.append(offset)
    
    try:
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                if item.get('raw_data'):
                    item.update(json.loads(item['raw_data']))
                if item.get('analysis'):
                    item['analysis'] = json.loads(item['analysis'])
                if item.get('tags'):
                    item['tags'] = json.loads(item['tags'])
                if item.get('entities'):
                    item['entities'] = json.loads(item['entities'])
                result.append(item)
            except:
                result.append(item)
        return result
    except Exception as e:
        print(f"Error getting filtered news: {e}")
        return []
    finally:
        conn.close()

def get_top_entities(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Aggregate entities from recent news (last 1000 items to keep it fast)
        cursor.execute("SELECT entities FROM news WHERE entities IS NOT NULL AND entities != '{}' ORDER BY created_at DESC LIMIT 1000")
        rows = cursor.fetchall()
        
        entity_counts = {}
        for row in rows:
            try:
                ents = json.loads(row['entities'])
                if isinstance(ents, dict):
                    for name, desc in ents.items():
                        entity_counts[name] = entity_counts.get(name, 0) + 1
            except:
                pass
        
        # Sort by count
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"name": name, "count": count} for name, count in sorted_entities]
    except Exception as e:
        print(f"Error getting top entities: {e}")
        return []
    finally:
        conn.close()

# Initialize on import if needed, but better to call explicitly
# init_db()
