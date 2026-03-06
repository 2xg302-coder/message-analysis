import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import difflib
from core.database import db
from core.logging import get_logger

logger = get_logger("news_service")

class NewsService:
    def __init__(self, database=None):
        self.db = database or db

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

    def _prepare_news_params(self, news_item: Dict[str, Any]) -> tuple:
        record = news_item.copy()
        if 'created_at' not in record:
            record['created_at'] = datetime.now().isoformat()
        
        # Serialize JSON fields with ensure_ascii=False to save Chinese characters directly
        tags = json.dumps(record.get('tags', []), ensure_ascii=False) if isinstance(record.get('tags'), list) else record.get('tags')
        entities = json.dumps(record.get('entities', {}), ensure_ascii=False) if isinstance(record.get('entities'), dict) else record.get('entities')
        simhash_val = str(record.get('simhash')) if record.get('simhash') is not None else None

        return (
            record.get('id'),
            record.get('title', ''),
            record.get('link', ''),
            record.get('content', ''),
            record.get('time', ''),
            record.get('timestamp', ''),
            record.get('scrapedAt', ''),
            record['created_at'],
            record.get('source', 'unknown'),
            json.dumps(record, ensure_ascii=False),
            record.get('type', 'article'),
            tags,
            entities,
            record.get('impact_score', 0),
            record.get('sentiment_score', 0.0),
            simhash_val
        )

    async def add_news(self, news_item: Dict[str, Any]) -> bool:
        if not news_item or 'id' not in news_item:
            return False
            
        try:
            # Check existence first (optional optimization: let INSERT OR IGNORE handle it)
            # existing = await self.db.execute_query('SELECT id FROM news WHERE id = ?', (news_item['id'],))
            # if existing:
            #    return False
                
            params = self._prepare_news_params(news_item)

            query = '''
                INSERT OR IGNORE INTO news (
                    id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data,
                    type, tags, entities, impact_score, sentiment_score, simhash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            return await self.db.execute_update(query, params)
        except Exception as e:
            logger.error(f"Error adding news: {e}")
            return False

    async def add_news_batch(self, news_list: List[Dict[str, Any]]) -> int:
        if not news_list:
            return 0
            
        try:
            params_list = []
            for item in news_list:
                if 'id' in item:
                    params_list.append(self._prepare_news_params(item))
            
            if not params_list:
                return 0

            query = '''
                INSERT OR IGNORE INTO news (
                    id, title, link, content, time, timestamp, scraped_at, created_at, source, raw_data,
                    type, tags, entities, impact_score, sentiment_score, simhash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            return await self.db.execute_many(query, params_list)
        except Exception as e:
            logger.error(f"Error adding news batch: {e}")
            return 0

    async def get_news(self, limit: int = 100, offset: int = 0, 
                 news_type: Optional[str] = None, 
                 min_impact: Optional[int] = None,
                 tag: Optional[str] = None,
                 sentiment: Optional[str] = None,
                 keyword: Optional[str] = None,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 return_total: bool = False) -> Any:
        
        where_clauses = ["1=1"]
        params = []
        
        if news_type:
            where_clauses.append("type = ?")
            params.append(news_type)
            
        if min_impact is not None:
            where_clauses.append("impact_score >= ?")
            params.append(min_impact)

        if tag:
            escaped_tag = json.dumps(tag).strip('"')
            where_clauses.append("(tags LIKE ? OR tags LIKE ?)")
            params.append(f'%{tag}%')
            params.append(f'%{escaped_tag}%')

        if sentiment:
            if sentiment == 'positive':
                where_clauses.append("sentiment_score > ?")
                params.append(0.05)
            elif sentiment == 'negative':
                where_clauses.append("sentiment_score < ?")
                params.append(-0.05)
            elif sentiment == 'neutral':
                where_clauses.append("sentiment_score >= ? AND sentiment_score <= ?")
                params.extend([-0.05, 0.05])

        if keyword:
            # Search in title, content, or entities
            # entities is stored as JSON string, so LIKE works
            where_clauses.append("(title LIKE ? OR content LIKE ? OR entities LIKE ?)")
            kw_param = f'%{keyword}%'
            params.extend([kw_param, kw_param, kw_param])

        if start_date and end_date:
            where_clauses.append("created_at >= ? AND created_at <= ?")
            params.extend([start_date, end_date + "T23:59:59.999999"])
            
        where_sql = " AND ".join(where_clauses)
        
        # 1. Get Data
        query = f"SELECT * FROM news WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        query_params = params + [limit, offset]
        
        rows = await self.db.execute_query(query, tuple(query_params))
        news_list = [self._process_news_item(row) for row in rows]
        
        if not return_total:
            return news_list
            
        # 2. Get Total Count
        count_query = f"SELECT COUNT(*) as count FROM news WHERE {where_sql}"
        count_res = await self.db.execute_query(count_query, tuple(params))
        total = count_res[0]['count'] if count_res else 0
        
        return news_list, total

    async def get_unanalyzed_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        query = 'SELECT * FROM news WHERE analysis IS NULL ORDER BY created_at ASC LIMIT ?'
        rows = await self.db.execute_query(query, (limit,))
        return [self._process_news_item(row) for row in rows]

    async def save_analysis(self, news_id: str, analysis_result: Dict[str, Any]) -> bool:
        try:
            updates = {
                'analysis': json.dumps(analysis_result, ensure_ascii=False),
                'analyzed_at': datetime.now().isoformat()
            }
            
            if 'impact_score' in analysis_result:
                updates['impact_score'] = analysis_result['impact_score']
            if 'sentiment_score' in analysis_result:
                updates['sentiment_score'] = analysis_result['sentiment_score']
            if 'tags' in analysis_result:
                updates['tags'] = json.dumps(analysis_result['tags'], ensure_ascii=False)
            if 'entities' in analysis_result:
                updates['entities'] = json.dumps(analysis_result['entities'], ensure_ascii=False)

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values())
            values.append(news_id)
            
            query = f'UPDATE news SET {set_clause} WHERE id = ?'
            return await self.db.execute_update(query, tuple(values))
        except Exception as e:
            logger.error(f"Error saving analysis for {news_id}: {e}")
            return False

    async def delete_news(self, news_id: str) -> bool:
        try:
            query = "DELETE FROM news WHERE id = ?"
            return await self.db.execute_update(query, (news_id,))
        except Exception as e:
            logger.error(f"Error deleting news {news_id}: {e}")
            return False

    async def get_tag_stats(self, limit: int = 100, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT tags FROM news WHERE tags IS NOT NULL AND tags != '[]'"
        params = []
        
        # Determine row limit based on context
        if start_date and end_date:
            query += " AND created_at >= ? AND created_at <= ?"
            params.extend([start_date, end_date + "T23:59:59.999999"])
            # When filtering by date, we want accuracy over the whole period
            row_limit = 50000
        else:
            # Default to analyzing recent 5000 items for trends
            row_limit = 5000
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(row_limit)
        
        rows = await self.db.execute_query(query, tuple(params))
        
        from collections import Counter
        tag_counts = Counter()
        
        for row in rows:
            tags = self._parse_json_field(row['tags'], [])
            if isinstance(tags, list):
                tag_counts.update(tags)
        
        return [{"name": name, "value": count} for name, count in tag_counts.most_common(limit)]

    async def get_type_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT analysis FROM news WHERE analysis IS NOT NULL"
        params = []
        if start_date and end_date:
            query += " AND created_at >= ? AND created_at <= ?"
            params.extend([start_date, end_date + "T23:59:59.999999"])
        query += " ORDER BY created_at DESC LIMIT 2000"
        
        rows = await self.db.execute_query(query, tuple(params))
        type_counts = {}
        for row in rows:
            analysis = self._parse_json_field(row['analysis'], {})
            etype = analysis.get('event_type', '其他')
            type_counts[etype] = type_counts.get(etype, 0) + 1
            
        return [{"name": name, "value": count} for name, count in type_counts.items()]

    async def get_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        try:
            where_clause = ""
            params = []
            if start_date and end_date:
                where_clause = " WHERE created_at >= ? AND created_at <= ?"
                params.extend([start_date, end_date + "T23:59:59.999999"])

            total_query = f'SELECT COUNT(*) as count FROM news{where_clause}'
            total_res = await self.db.execute_query(total_query, tuple(params))
            total = total_res[0]['count'] if total_res else 0
            
            analyzed_where = where_clause + (" AND" if where_clause else " WHERE") + " analysis IS NOT NULL"
            analyzed_query = f'SELECT COUNT(*) as count FROM news{analyzed_where}'
            analyzed_res = await self.db.execute_query(analyzed_query, tuple(params))
            analyzed = analyzed_res[0]['count'] if analyzed_res else 0
            
            trends_query = f'''
                SELECT substr(created_at, 12, 2) as hour, count(*) as count 
                FROM news 
                {where_clause}
                GROUP BY hour 
                ORDER BY hour DESC 
                LIMIT 12
            '''
            trends = await self.db.execute_query(trends_query, tuple(params))
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

    async def get_top_entities(self, limit: int = 50, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT entities FROM news WHERE entities IS NOT NULL"
        params = []
        if start_date and end_date:
            query += " AND created_at >= ? AND created_at <= ?"
            params.extend([start_date, end_date + "T23:59:59.999999"])
        query += " ORDER BY created_at DESC LIMIT 1000"

        rows = await self.db.execute_query(query, tuple(params))
        entity_counts = {}
        
        for row in rows:
            ents = self._parse_json_field(row['entities'], {})
            if isinstance(ents, dict):
                for name in ents.keys():
                    entity_counts[name] = entity_counts.get(name, 0) + 1
            elif isinstance(ents, list):
                for item in ents:
                    name = None
                    if isinstance(item, dict):
                        name = item.get('name')
                    elif isinstance(item, str):
                        name = item
                    
                    if name:
                        entity_counts[name] = entity_counts.get(name, 0) + 1
                
        sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"name": name, "count": count} for name, count in sorted_entities]

    def _merge_similar_tags(self, series_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge similar tags to reduce fragmentation.
        Strategy:
        1. Substring merging: Merge longer tags into shorter parent tags (e.g., "OpenAI内斗" -> "OpenAI").
        2. Fuzzy merging: Merge low-frequency tags into high-frequency similar tags (e.g., typos).
        """
        if not series_list:
            return []
            
        # Sort by length (asc) for substring merging
        # We process shortest tags first, treating them as potential parents
        sorted_by_len = sorted(series_list, key=lambda x: len(x['tag']))
        
        # Use a dictionary to track merged results: tag -> data
        # We initiate it with all items, but we will modify it
        # Actually better to build it up
        merged_map = {}
        
        # Pass 1: Substring Merging (Long -> Short)
        # We iterate through sorted_by_len. For each tag, we check if it can be merged into an existing (shorter) tag in merged_map.
        # But wait, if we have "A", "AB", "ABC".
        # 1. Process "A". Add to map.
        # 2. Process "AB". Check if "A" in "AB". Yes. Merge "AB" into "A".
        # 3. Process "ABC". Check if "A" in "ABC". Yes. Merge "ABC" into "A".
        
        for item in sorted_by_len:
            tag = item['tag']
            merged = False
            
            # Try to find a parent in the already processed items (which are shorter or equal length)
            # We iterate over keys of merged_map to find a parent
            for parent_tag in list(merged_map.keys()):
                # Rule 1: Parent must be at least 2 chars to avoid over-merging generic chars
                if len(parent_tag) < 2: 
                    continue
                
                # Rule 2: Substring match (parent is substring of current tag)
                if parent_tag in tag:
                    # Merge current (longer) into parent (shorter)
                    parent_data = merged_map[parent_tag]
                    parent_data['count'] += item['count']
                    # Keep the latest date
                    if item['latest_date'] > parent_data['latest_date']:
                        parent_data['latest_date'] = item['latest_date']
                    # Keep the longer summary if parent has none or short one? 
                    # Actually let's just keep the parent's summary unless empty
                    if not parent_data.get('sample_summary') and item.get('sample_summary'):
                        parent_data['sample_summary'] = item['sample_summary']
                        
                    merged = True
                    break
            
            if not merged:
                merged_map[tag] = item

        # Pass 2: Fuzzy Merging (Levenshtein)
        # Now we work with the result of Pass 1
        # Sort by frequency DESC to prioritize keeping popular tags
        current_list = sorted(merged_map.values(), key=lambda x: x['count'], reverse=True)
        final_map = {}
        
        for item in current_list:
            tag = item['tag']
            merged = False
            
            for main_tag in list(final_map.keys()):
                # Skip if length diff is too big (optimization)
                if abs(len(tag) - len(main_tag)) > 3:
                    continue
                    
                # Calculate similarity
                ratio = difflib.SequenceMatcher(None, tag, main_tag).ratio()
                # Threshold 0.8 is conservative enough for typos or very close variants
                if ratio > 0.8:
                    # Merge current (lower freq) into main (higher freq)
                    main_data = final_map[main_tag]
                    main_data['count'] += item['count']
                    if item['latest_date'] > main_data['latest_date']:
                        main_data['latest_date'] = item['latest_date']
                    merged = True
                    break
            
            if not merged:
                final_map[tag] = item
                
        return sorted(final_map.values(), key=lambda x: (x['count'], x['latest_date']), reverse=True)

    async def get_series_list(self) -> List[Dict[str, Any]]:
        rows = await self.db.execute_query("SELECT analysis, created_at FROM news WHERE analysis IS NOT NULL AND analysis LIKE '%\"event_tag\"%' ORDER BY created_at DESC LIMIT 2000")
        series_map = {}
        
        for row in rows:
            analysis = self._parse_json_field(row['analysis'], {})
            tag = analysis.get('event_tag')
            if tag:
                # Basic cleaning
                tag = tag.strip()
                if not tag: continue
                
                if tag not in series_map:
                    series_map[tag] = {
                        'tag': tag,
                        'count': 0,
                        'latest_date': row['created_at'],
                        'sample_summary': analysis.get('summary')
                    }
                series_map[tag]['count'] += 1
        
        # Convert map to list
        raw_list = list(series_map.values())
        
        # Apply merging logic
        merged_list = self._merge_similar_tags(raw_list)
        
        return merged_list

    async def get_news_by_series(self, tag: str) -> List[Dict[str, Any]]:
        rows = await self.db.execute_query("SELECT * FROM news WHERE analysis LIKE ? ORDER BY created_at DESC", (f'%{tag}%',))
        result = []
        for row in rows:
            item = self._process_news_item(row)
            event_tag = item.get('analysis', {}).get('event_tag')
            # Relaxed match: 
            # 1. Exact match (legacy behavior)
            # 2. Tag is substring of event_tag (handles merged cases like "OpenAI" matching "OpenAI内斗")
            if event_tag and (tag == event_tag or tag in event_tag):
                result.append(item)
        return result

    async def _calculate_similarity(self, series: Dict[str, Any], tag: str, target_entities: set, other_entities_map: Dict[str, set]) -> Optional[Dict[str, Any]]:
        """Helper to calculate similarity for a single series (async)"""
        try:
            other_tag = series['tag']
            if other_tag == tag:
                return None
                
            other_entities = other_entities_map.get(other_tag, set())
            
            if not other_entities:
                return None

            intersection = target_entities.intersection(other_entities)
            union = target_entities.union(other_entities)
            
            if not union:
                score = 0
            else:
                score = len(intersection) / len(union)

            if score > 0:
                return {
                    'tag': other_tag,
                    'score': score,
                    'shared_entities': list(intersection)[:3],
                    'count': series['count'],
                    'latest_date': series['latest_date']
                }
            return None
        except Exception as e:
            logger.error(f"Error comparing series {tag} vs {series.get('tag')}: {e}")
            return None

    async def get_related_series(self, tag: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Calculate correlation between event series based on shared entities using Jaccard similarity.
        Optimized to batch fetch entities and avoid N+1 queries.
        """
        try:
            import asyncio
            
            # 1. Get entities for the target tag
            target_news = await self.get_news_by_series(tag)
            
            logger.info(f"Calculating related series for '{tag}'. Found {len(target_news)} news items.")
            
            if not target_news:
                return []

            def get_entity_set(news_list):
                entities = set()
                for item in news_list:
                    analysis = item.get('analysis', {})
                    if not analysis: continue
                    ents = analysis.get('entities', {})
                    
                    if isinstance(ents, dict):
                        entities.update(ents.keys())
                    elif isinstance(ents, list):
                        for e in ents:
                            if isinstance(e, dict):
                                name = e.get('name')
                            elif isinstance(e, str):
                                name = e
                            else:
                                name = None
                            if name and isinstance(name, str):
                                entities.add(name)
                return entities

            target_entities = get_entity_set(target_news)
            if not target_entities:
                logger.info(f"No entities found for tag '{tag}'")
                return []

            # 2. Get all other series
            all_series = await self.get_series_list()
            
            # Optimization: Filter top 50 series
            top_series = all_series[:50]
            top_tags = [s['tag'] for s in top_series if s['tag'] != tag]
            
            if not top_tags:
                return []

            # 3. Batch fetch news for all candidate series
            # We need to construct a query that fetches entities for all these tags
            # Since SQLite doesn't have array parameters easily, we'll fetch news where analysis contains any of these tags
            # OR we can just fetch ALL news with analysis and filter in memory? No, too big.
            # We can use OR conditions: analysis LIKE '%tag1%' OR analysis LIKE '%tag2%' ...
            # But with 50 tags, query might be long.
            # Alternative: Since we only need entities, we can optimize the query.
            
            # Let's construct a batch query
            placeholders = " OR ".join(["analysis LIKE ?"] * len(top_tags))
            params = [f'%{t}%' for t in top_tags]
            
            # We only need analysis field!
            query = f"SELECT analysis FROM news WHERE analysis IS NOT NULL AND ({placeholders}) ORDER BY created_at DESC LIMIT 5000"
            
            rows = await self.db.execute_query(query, tuple(params))
            
            # 4. Group entities by tag in memory
            other_entities_map = {} # tag -> set(entities)
            
            for row in rows:
                analysis = self._parse_json_field(row['analysis'], {})
                event_tag = analysis.get('event_tag')
                
                # Check which top_tag this news belongs to (handling the substring match logic)
                matched_tags = []
                for t in top_tags:
                    if event_tag and (t == event_tag or t in event_tag):
                        matched_tags.append(t)
                
                if not matched_tags:
                    continue
                    
                ents = analysis.get('entities', {})
                row_entities = set()
                if isinstance(ents, dict):
                    row_entities.update(ents.keys())
                elif isinstance(ents, list):
                    for e in ents:
                        name = e.get('name') if isinstance(e, dict) else e
                        if name and isinstance(name, str):
                            row_entities.add(name)
                            
                for t in matched_tags:
                    if t not in other_entities_map:
                        other_entities_map[t] = set()
                    other_entities_map[t].update(row_entities)

            # 5. Calculate similarities in memory (CPU bound, but fast for sets)
            tasks = []
            for series in top_series:
                tasks.append(self._calculate_similarity(series, tag, target_entities, other_entities_map))
            
            results = await asyncio.gather(*tasks)
            
            # Filter None results
            related_scores = [r for r in results if r is not None]

            # Sort by score DESC
            return sorted(related_scores, key=lambda x: x['score'], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Error calculating related series for {tag}: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def get_watchlist(self) -> List[str]:
        rows = await self.db.execute_query('SELECT keyword FROM watchlist ORDER BY created_at ASC')
        return [row['keyword'] for row in rows]

    async def update_watchlist(self, keywords: List[str]) -> bool:
        try:
            async with self.db.get_connection() as conn:
                await conn.execute('DELETE FROM watchlist')
                current_time = datetime.now().isoformat()
                if keywords:
                    await conn.executemany('INSERT INTO watchlist (keyword, created_at) VALUES (?, ?)',
                                         [(kw, current_time) for kw in keywords])
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating watchlist: {e}")
            return False

news_service = NewsService()