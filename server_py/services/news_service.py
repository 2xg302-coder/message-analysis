import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.database import db
from core.logging import get_logger

logger = get_logger("news_service")

class NewsService:
    def __init__(self):
        self.db = db

    def _parse_json_field(self, field: Any, default: Any) -> Any:
        if not field:
            return default
        if isinstance(field, (dict, list)):
            return field
        try:
            return json.loads(field)
        except (json.JSONDecodeError, TypeError):
            return default

    def _process_news_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw DB row into clean dictionary"""
        try:
            processed = dict(item)
            
            # Merge raw_data if exists
            if processed.get('raw_data'):
                try:
                    raw_data = json.loads(processed['raw_data'])
                    if isinstance(raw_data, dict):
                        processed.update(raw_data)
                except Exception:
                    pass
            
            # Parse complex fields
            processed['tags'] = self._parse_json_field(processed.get('tags'), [])
            processed['entities'] = self._parse_json_field(processed.get('entities'), {})
            processed['analysis'] = self._parse_json_field(processed.get('analysis'), None)
            
            return processed
        except Exception as e:
            logger.error(f"Error processing news item: {e}")
            return item

    def add_news(self, news_item: Dict[str, Any]) -> bool:
        if not news_item or 'id' not in news_item:
            return False
            
        try:
            # Check existence
            existing = self.db.execute_query('SELECT id FROM news WHERE id = ?', (news_item['id'],))
            if existing:
                return False
                
            record = news_item.copy()
            record['created_at'] = datetime.now().isoformat()
            
            # Serialize JSON fields
            tags = json.dumps(record.get('tags', [])) if isinstance(record.get('tags'), list) else record.get('tags')
            entities = json.dumps(record.get('entities', {})) if isinstance(record.get('entities'), dict) else record.get('entities')
            simhash_val = str(record.get('simhash')) if record.get('simhash') is not None else None

            query = '''
                INSERT INTO news (
                    id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data,
                    type, tags, entities, impact_score, sentiment_score, simhash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (
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
                simhash_val
            )
            
            return self.db.execute_update(query, params)
        except Exception as e:
            logger.error(f"Error adding news: {e}")
            return False

    def add_news_batch(self, news_list: List[Dict[str, Any]]) -> int:
        count = 0
        for item in news_list:
            if self.add_news(item):
                count += 1
        return count

    def get_news(self, limit: int = 100, offset: int = 0, 
                 news_type: Optional[str] = None, 
                 min_impact: Optional[int] = None) -> List[Dict[str, Any]]:
        
        query = "SELECT * FROM news WHERE 1=1"
        params = []
        
        if news_type:
            query += " AND type = ?"
            params.append(news_type)
            
        if min_impact is not None:
            query += " AND impact_score >= ?"
            params.append(min_impact)
            
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)
        
        rows = self.db.execute_query(query, tuple(params))
        return [self._process_news_item(row) for row in rows]

    def get_unanalyzed_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = 'SELECT * FROM news WHERE analysis IS NULL ORDER BY created_at ASC LIMIT ?'
        rows = self.db.execute_query(query, (limit,))
        return [self._process_news_item(row) for row in rows]

    def save_analysis(self, news_id: str, analysis_result: Dict[str, Any]) -> bool:
        try:
            updates = {
                'analysis': json.dumps(analysis_result),
                'analyzed_at': datetime.now().isoformat()
            }
            
            if 'impact_score' in analysis_result:
                updates['impact_score'] = analysis_result['impact_score']
            if 'sentiment_score' in analysis_result:
                updates['sentiment_score'] = analysis_result['sentiment_score']
            if 'tags' in analysis_result:
                updates['tags'] = json.dumps(analysis_result['tags'])
            if 'entities' in analysis_result:
                updates['entities'] = json.dumps(analysis_result['entities'])

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values())
            values.append(news_id)
            
            query = f'UPDATE news SET {set_clause} WHERE id = ?'
            return self.db.execute_update(query, tuple(values))
        except Exception as e:
            logger.error(f"Error saving analysis for {news_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        try:
            total = self.db.execute_query('SELECT COUNT(*) as count FROM news')[0]['count']
            analyzed = self.db.execute_query('SELECT COUNT(*) as count FROM news WHERE analysis IS NOT NULL')[0]['count']
            
            # Trends
            trends_query = '''
                SELECT substr(created_at, 12, 2) as hour, count(*) as count 
                FROM news 
                GROUP BY hour 
                ORDER BY hour DESC 
                LIMIT 12
            '''
            trends = self.db.execute_query(trends_query)
            trends.reverse()
            
            return {
                'total': total,
                'analyzed': analyzed,
                'pending': total - analyzed,
                'trends': trends
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'total': 0, 'analyzed': 0, 'pending': 0, 'trends': []}

    def get_top_entities(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self.db.execute_query("SELECT entities FROM news WHERE entities IS NOT NULL ORDER BY created_at DESC LIMIT 1000")
        entity_counts = {}
        
        for row in rows:
            ents = self._parse_json_field(row['entities'], {})
            for name, _ in ents.items():
                entity_counts[name] = entity_counts.get(name, 0) + 1
                
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"name": name, "count": count} for name, count in sorted_entities]

    def get_series_list(self) -> List[Dict[str, Any]]:
        rows = self.db.execute_query("SELECT analysis, created_at FROM news WHERE analysis IS NOT NULL AND analysis LIKE '%\"event_tag\"%' ORDER BY created_at DESC LIMIT 2000")
        series_map = {}
        
        for row in rows:
            analysis = self._parse_json_field(row['analysis'], {})
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
                
        return sorted(series_map.values(), key=lambda x: x['latest_date'], reverse=True)

    def get_news_by_series(self, tag: str) -> List[Dict[str, Any]]:
        rows = self.db.execute_query("SELECT * FROM news WHERE analysis LIKE ? ORDER BY created_at DESC", (f'%{tag}%',))
        result = []
        for row in rows:
            item = self._process_news_item(row)
            if item.get('analysis', {}).get('event_tag') == tag:
                result.append(item)
        return result

    def get_watchlist(self) -> List[str]:
        rows = self.db.execute_query('SELECT keyword FROM watchlist ORDER BY created_at ASC')
        return [row['keyword'] for row in rows]

    def update_watchlist(self, keywords: List[str]) -> bool:
        # Transactional update
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM watchlist')
            current_time = datetime.now().isoformat()
            for kw in keywords:
                cursor.execute('INSERT INTO watchlist (keyword, created_at) VALUES (?, ?)', (kw, current_time))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating watchlist: {e}")
            return False
        finally:
            conn.close()

news_service = NewsService()
