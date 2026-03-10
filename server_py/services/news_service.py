import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
import difflib
import re
import unicodedata
from collections import Counter
from simhash import Simhash
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
            processed['triples'] = self._parse_json_field(processed.get('triples'), [])
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
        triples = json.dumps(record.get('triples', []), ensure_ascii=False) if isinstance(record.get('triples'), list) else record.get('triples')
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
            triples,
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
                    type, tags, entities, triples, impact_score, sentiment_score, simhash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    type, tags, entities, triples, impact_score, sentiment_score, simhash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                 source: Optional[str] = None,
                 return_total: bool = False) -> Any:
        
        where_clauses = ["1=1"]
        params = []
        
        if news_type:
            where_clauses.append("type = ?")
            params.append(news_type)
            
        if min_impact is not None:
            where_clauses.append("impact_score >= ?")
            params.append(min_impact)

        if source:
            where_clauses.append("source = ?")
            params.append(source)

        if tag:
            where_clauses.append("EXISTS (SELECT 1 FROM json_each(news.tags) WHERE json_each.value = ?)")
            params.append(tag)

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
        # 优先处理当日新闻（随机抽取），其余按随机顺序处理
        # 逻辑：
        # 1. 按照 "是否是今天" 进行分层，今天的新闻优先级高 (0)，往日新闻优先级低 (1)
        # 2. 在同一层级内，使用 RANDOM() 进行随机抽取
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        query = '''
            SELECT * FROM news 
            WHERE analysis IS NULL 
            ORDER BY 
                CASE WHEN created_at >= ? THEN 0 ELSE 1 END ASC,
                RANDOM()
            LIMIT ?
        '''
        rows = await self.db.execute_query(query, (today_start, limit))
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
            if 'triples' in analysis_result:
                updates['triples'] = json.dumps(analysis_result['triples'], ensure_ascii=False)

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

    def _normalize_for_simhash(self, text: str) -> str:
        if not text:
            return ""
        text = str(text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"【免责声明】.*", "", text)
        text = re.sub(r"（记者\s+.*?）", "", text)
        text = re.sub(r"\(记者\s+.*?\)", "", text)
        text = re.sub(r"^.{2,6}\d{1,2}月\d{1,2}日[电讯][，,]", "", text)
        text = re.sub(r"^【.*?】", "", text)
        return " ".join(text.strip().split())

    def _normalize_for_compare(self, text: str) -> str:
        if not text:
            return ""
        text = self._normalize_for_simhash(text)
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"[，。、“”‘’；：！？,.!?:;\"'（）()【】\[\]<>《》—\-·]", "", text)
        return text

    def _pick_keep_delete(self, item_a: Dict[str, Any], item_b: Dict[str, Any]) -> tuple:
        """
        返回 (keep_item, delete_item)
        规则：
        1) 优先保留内容更长者；
        2) 长度相同保留更早 created_at；
        3) 仍相同按 id 字典序稳定排序。
        """
        text_a = item_a.get("content") or item_a.get("title") or ""
        text_b = item_b.get("content") or item_b.get("title") or ""
        len_a, len_b = len(text_a), len(text_b)

        if len_a > len_b:
            return item_a, item_b
        if len_b > len_a:
            return item_b, item_a

        created_a = item_a.get("created_at") or ""
        created_b = item_b.get("created_at") or ""
        if created_a < created_b:
            return item_a, item_b
        if created_b < created_a:
            return item_b, item_a

        if (item_a.get("id") or "") <= (item_b.get("id") or ""):
            return item_a, item_b
        return item_b, item_a

    def _clean_title(self, text: str) -> str:
        """Specific cleaning for Titles"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove source prefixes like "财联社3月6日电，" or "财联社3月6日讯，"
        # Pattern: 2-6 chars (source) + date + 电/讯 + comma/space/colon
        text = re.sub(r'^.{2,6}\d{1,2}月\d{1,2}日[电讯][，,:：\s]', '', text)
        
        # Remove brackets but keep content
        text = re.sub(r'[【】\[\]]', ' ', text)
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    async def scan_cross_source_duplicates(
        self,
        lookback_hours: int = 24,
        limit: int = 300,
        distance_threshold: int = 6,
        min_text_len: int = 20
    ) -> Dict[str, Any]:
        """
        扫描跨 source 的相似新闻对，给出建议删除项。
        """
        since = (datetime.now() - timedelta(hours=max(1, lookback_hours))).isoformat()
        capped_limit = max(10, min(limit, 1000))
        query = """
            SELECT id, source, title, content, created_at, simhash
            FROM news
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = await self.db.execute_query(query, (since, capped_limit))
        if not rows:
            return {
                "total_candidates": 0,
                "pairs_count": 0,
                "pairs": [],
                "recommended_delete_ids": []
            }

        candidates: List[Dict[str, Any]] = []
        for row in rows:
            raw_text = row.get("content") or row.get("title") or ""
            text = self._normalize_for_simhash(raw_text)
            compare_text = self._normalize_for_compare(raw_text)
            if len(compare_text) < min_text_len:
                continue
            sh = None
            raw_sh = row.get("simhash")
            if raw_sh is not None and str(raw_sh).strip() != "":
                try:
                    sh = Simhash(int(str(raw_sh)))
                except Exception:
                    sh = None
            if sh is None:
                try:
                    sh = Simhash(text)
                except Exception:
                    continue

            prepared = dict(row)
            prepared["_clean_text"] = text
            prepared["_compare_text"] = compare_text
            prepared["_clean_title"] = self._clean_title(row.get("title", ""))
            
            # Parse datetime for comparison
            try:
                dt_str = row.get("created_at")
                if dt_str:
                    prepared["_dt"] = datetime.fromisoformat(dt_str)
                else:
                    prepared["_dt"] = datetime.min
            except:
                prepared["_dt"] = datetime.min
                
            prepared["_simhash_obj"] = sh
            candidates.append(prepared)

        pairs: List[Dict[str, Any]] = []
        recommended_delete_ids = set()
        seen_pair_keys = set()

        for i in range(len(candidates)):
            left = candidates[i]
            for j in range(i + 1, len(candidates)):
                right = candidates[j]
                
                # Allow cross-source AND same-source checks
                same_source = left.get("source") == right.get("source")
                
                # Calculate time diff
                time_diff = abs((left["_dt"] - right["_dt"]).total_seconds())
                
                # Adjust thresholds for same-source & short time interval
                current_dist_threshold = distance_threshold
                if same_source and time_diff < 300: # 5 mins
                    current_dist_threshold = max(current_dist_threshold, 12) # Relaxed (larger distance allowed) - wait SimHash distance logic?
                    # SimHash distance: 0 is identical. 
                    # If we want to catch MORE duplicates (relaxed), we should INCREASE the threshold.
                    # Default is 6. If same source & close time, we expect high similarity but maybe slight changes.
                    # Wait, if same source, usually they are IDENTICAL or near identical.
                    # But user case is "content almost same".
                    # Let's use 6 as base. If same source & < 5min, maybe allow 8?
                    # Actually, if same source, we might want stricter?
                    # No, user complained about duplicates NOT being caught. So we need to catch MORE.
                    # So we relax the condition (increase threshold).
                    pass

                distance = left["_simhash_obj"].distance(right["_simhash_obj"])
                similar = distance <= current_dist_threshold
                reason = "simhash"

                if not similar:
                    lt = left["_compare_text"]
                    rt = right["_compare_text"]
                    shorter, longer = (lt, rt) if len(lt) <= len(rt) else (rt, lt)
                    if shorter and len(shorter) >= min_text_len and shorter in longer:
                        similar = True
                        reason = "containment"

                ratio = 0.0
                if not similar:
                    lt = left["_compare_text"]
                    rt = right["_compare_text"]
                    if lt and rt:
                        ratio = difflib.SequenceMatcher(None, lt[:600], rt[:600]).ratio()
                        if ratio >= 0.93:
                            similar = True
                            reason = "ratio"
                            
                # Title Check
                if not similar:
                    lt_title = left["_clean_title"]
                    rt_title = right["_clean_title"]
                    if lt_title and rt_title:
                        # Title Containment
                        if len(lt_title) > 5 and len(rt_title) > 5:
                            if lt_title in rt_title or rt_title in lt_title:
                                similar = True
                                reason = "title_containment"
                        
                        # Title Similarity
                        if not similar and len(lt_title) > 8 and len(rt_title) > 8:
                            title_ratio = difflib.SequenceMatcher(None, lt_title, rt_title).ratio()
                            title_threshold = 0.85
                            if same_source and time_diff < 300:
                                title_threshold = 0.6 # Relaxed for same source & time
                            
                            if title_ratio > title_threshold:
                                similar = True
                                reason = "title_similarity"

                if not similar:
                    continue

                keep_item, delete_item = self._pick_keep_delete(left, right)
                pair_key = tuple(sorted([left["id"], right["id"]]))
                if pair_key in seen_pair_keys:
                    continue
                seen_pair_keys.add(pair_key)

                recommended_delete_ids.add(delete_item["id"])
                pairs.append({
                    "reason": reason,
                    "distance": distance,
                    "ratio": ratio,
                    "left": {
                        "id": left["id"],
                        "source": left.get("source"),
                        "title": left.get("title", ""),
                        "created_at": left.get("created_at")
                    },
                    "right": {
                        "id": right["id"],
                        "source": right.get("source"),
                        "title": right.get("title", ""),
                        "created_at": right.get("created_at")
                    },
                    "keep_id": keep_item["id"],
                    "delete_id": delete_item["id"]
                })

        return {
            "total_candidates": len(candidates),
            "pairs_count": len(pairs),
            "pairs": pairs,
            "recommended_delete_ids": sorted(recommended_delete_ids)
        }

    async def delete_news_batch(self, news_ids: List[str]) -> int:
        clean_ids = [nid for nid in news_ids if nid]
        if not clean_ids:
            return 0
        placeholders = ",".join(["?"] * len(clean_ids))
        query = f"DELETE FROM news WHERE id IN ({placeholders})"
        try:
            async with self.db.get_connection() as conn:
                cursor = await conn.execute(query, tuple(clean_ids))
                await conn.commit()
                return cursor.rowcount or 0
        except Exception as e:
            logger.error(f"Error deleting news batch: {e}")
            return 0

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

    async def get_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None, exclude_source: Optional[str] = None) -> Dict[str, Any]:
        try:
            where_clause = ""
            params = []
            if start_date and end_date:
                where_clause = " WHERE created_at >= ? AND created_at <= ?"
                params.extend([start_date, end_date + "T23:59:59.999999"])
            
            if exclude_source:
                prefix = " AND" if where_clause else " WHERE"
                where_clause += f"{prefix} source != ?"
                params.append(exclude_source)

            total_query = f'SELECT COUNT(*) as count FROM news{where_clause}'
            total_res = await self.db.execute_query(total_query, tuple(params))
            total = total_res[0]['count'] if total_res else 0
            
            analyzed_where = where_clause + (" AND" if where_clause else " WHERE") + " analysis IS NOT NULL"
            analyzed_query = f'SELECT COUNT(*) as count FROM news{analyzed_where}'
            analyzed_res = await self.db.execute_query(analyzed_query, tuple(params))
            analyzed = analyzed_res[0]['count'] if analyzed_res else 0
            
            # Trend Query - Last 24 hours or specified range
            trend_params = list(params)
            trend_where = where_clause
            
            if not start_date and not end_date:
                # Default to last 24 hours if no range specified
                now = datetime.now()
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                cutoff = (current_hour - timedelta(hours=23)).isoformat()
                
                # Careful not to duplicate WHERE
                if not trend_where:
                     trend_where = " WHERE created_at >= ?"
                     trend_params = [cutoff]
                else:
                     trend_where += " AND created_at >= ?"
                     trend_params.append(cutoff)
            
            trends_query = f'''
                SELECT 
                    substr(created_at, 12, 2) || ':00' as hour, 
                    count(*) as count, 
                    sum(case when analysis is not null then 1 else 0 end) as analyzed_count,
                    substr(created_at, 1, 13) as date_hour
                FROM news 
                {trend_where}
                GROUP BY date_hour 
                ORDER BY date_hour ASC 
            '''
            
            # If no specific range, limit to 24 (though date filter should handle it mostly)
            if not start_date and not end_date:
                # We need enough rows to cover 24 hours, but GROUP BY reduces rows.
                # Removing LIMIT on source query to ensure aggregation is correct.
                pass
                
            trends = await self.db.execute_query(trends_query, tuple(trend_params))
            
            # Post-process to ensure full 24h timeline if default range
            if not start_date and not end_date:
                now = datetime.now()
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                
                # Create map from DB results
                # row['date_hour'] format from SQLite substr is "YYYY-MM-DDTHH"
                data_map = {row['date_hour']: {'count': row['count'], 'analyzed_count': row['analyzed_count']} for row in trends}
                
                full_trends = []
                # Generate last 24 hours (including current hour)
                # 0 to 23 hours ago
                for i in range(23, -1, -1):
                    t = current_hour - timedelta(hours=i)
                    key = t.strftime("%Y-%m-%dT%H")
                    
                    label = t.strftime("%H:00")
                    
                    entry = data_map.get(key, {'count': 0, 'analyzed_count': 0})
                    
                    full_trends.append({
                        "hour": label,
                        "count": entry['count'],
                        "analyzed_count": entry['analyzed_count'],
                        "date_hour": key
                    })
                trends = full_trends
            
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

    def _extract_entity_names(self, entities_data: Any) -> Set[str]:
        names: Set[str] = set()
        if isinstance(entities_data, dict):
            for key in entities_data.keys():
                if isinstance(key, str) and key.strip():
                    names.add(key.strip())
            return names
        if isinstance(entities_data, list):
            for item in entities_data:
                candidate = None
                if isinstance(item, dict):
                    candidate = item.get("name")
                elif isinstance(item, str):
                    candidate = item
                if isinstance(candidate, str) and candidate.strip():
                    names.add(candidate.strip())
        return names

    def _normalize_entity_name(self, name: str) -> str:
        if not isinstance(name, str):
            return ""
        text = unicodedata.normalize("NFKC", name).strip()
        if not text:
            return ""
        alias_map = {
            "usa": "美国",
            "u.s.": "美国",
            "u.s": "美国",
            "united states": "美国",
            "prc": "中国",
            "russia": "俄罗斯",
            "uk": "英国",
            "u.k.": "英国",
            "eu": "欧盟",
            "u.n.": "联合国",
            "un": "联合国"
        }
        lowered = text.lower()
        if lowered in alias_map:
            text = alias_map[lowered]
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"[·•．・]", "", text)
        text = re.sub(r"[，。、“”‘’；：！？,.!?:;\"'（）()【】\[\]<>《》—\-_/|]", "", text)
        return text.lower()

    def _pick_entity_cluster_representative(self, names: List[str], freq_counter: Counter) -> str:
        scored = sorted(
            names,
            key=lambda n: (-freq_counter.get(n, 0), len(n), n)
        )
        return scored[0]

    def _build_entity_clusters(self, all_entities: Set[str], freq_counter: Counter) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
        if not all_entities:
            return {}, {}
        normalized_buckets: Dict[str, List[str]] = {}
        for name in all_entities:
            normalized = self._normalize_entity_name(name)
            if not normalized:
                continue
            normalized_buckets.setdefault(normalized, []).append(name)

        canonical_map: Dict[str, str] = {}
        cluster_variants: Dict[str, Set[str]] = {}

        normalized_keys = sorted(normalized_buckets.keys(), key=lambda x: len(x))
        consumed_keys: Set[str] = set()
        fuzzy_threshold = 0.88

        for key in normalized_keys:
            if key in consumed_keys:
                continue
            cluster_keys = [key]
            consumed_keys.add(key)
            for other_key in normalized_keys:
                if other_key in consumed_keys:
                    continue
                if len(key) >= 2 and key in other_key:
                    cluster_keys.append(other_key)
                    consumed_keys.add(other_key)
                    continue
                if abs(len(key) - len(other_key)) > 4:
                    continue
                ratio = difflib.SequenceMatcher(None, key, other_key).ratio()
                if ratio >= fuzzy_threshold:
                    cluster_keys.append(other_key)
                    consumed_keys.add(other_key)

            cluster_names: List[str] = []
            for cluster_key in cluster_keys:
                cluster_names.extend(normalized_buckets.get(cluster_key, []))
            representative = self._pick_entity_cluster_representative(cluster_names, freq_counter)
            variants = set(cluster_names)
            cluster_variants[representative] = variants
            for variant in variants:
                canonical_map[variant] = representative

        return canonical_map, cluster_variants

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
                shared_entities = sorted(list(intersection), key=lambda x: (-len(x), x))[:3]
                return {
                    'tag': other_tag,
                    'score': score,
                    'shared_entities': shared_entities,
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
                    if not analysis:
                        continue
                    entities.update(self._extract_entity_names(analysis.get('entities', {})))
                return entities

            target_raw_entities = get_entity_set(target_news)
            target_entities = set(target_raw_entities)
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
            other_entities_map = {}
            
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
                    
                row_entities = self._extract_entity_names(analysis.get('entities', {}))
                            
                for t in matched_tags:
                    if t not in other_entities_map:
                        other_entities_map[t] = set()
                    other_entities_map[t].update(row_entities)

            all_entities = set(target_raw_entities)
            for ents in other_entities_map.values():
                all_entities.update(ents)

            if all_entities:
                entity_frequency = Counter()
                for entity in target_raw_entities:
                    entity_frequency[entity] += 1
                for ents in other_entities_map.values():
                    for entity in ents:
                        entity_frequency[entity] += 1

                canonical_map, _ = self._build_entity_clusters(all_entities, entity_frequency)
                if canonical_map:
                    target_entities = {canonical_map.get(entity, entity) for entity in target_raw_entities}
                    normalized_other_map = {}
                    for other_tag, raw_entities in other_entities_map.items():
                        normalized_other_map[other_tag] = {canonical_map.get(entity, entity) for entity in raw_entities}
                    other_entities_map = normalized_other_map

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

    async def get_monitor_stats(self) -> Dict[str, Any]:
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # Collected Today
            collected_query = "SELECT COUNT(*) as count FROM news WHERE created_at >= ?"
            collected_res = await self.db.execute_query(collected_query, (today_str,))
            collected_today = collected_res[0]['count'] if collected_res else 0

            processed_query = "SELECT COUNT(*) as count FROM news WHERE analyzed_at >= ? AND analysis IS NOT NULL AND analysis != ''"
            processed_res = await self.db.execute_query(processed_query, (today_str,))
            processed_today = processed_res[0]['count'] if processed_res else 0
            
            # Pending (Backlog)
            pending_query = "SELECT COUNT(*) as count FROM news WHERE analysis IS NULL OR analysis = ''"
            pending_res = await self.db.execute_query(pending_query)
            pending_count = pending_res[0]['count'] if pending_res else 0
            
            # Failed Today
            failed_query = "SELECT COUNT(*) as count FROM news WHERE analysis LIKE '%error%' AND created_at >= ?"
            failed_res = await self.db.execute_query(failed_query, (today_str,))
            failed_today = failed_res[0]['count'] if failed_res else 0
            
            return {
                "collected_today": collected_today,
                "processed_today": processed_today,
                "pending_count": pending_count,
                "failed_today": failed_today
            }
        except Exception as e:
            logger.error(f"Error getting monitor stats: {e}")
            return {
                "collected_today": 0,
                "processed_today": 0,
                "pending_count": 0,
                "failed_today": 0
            }

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
