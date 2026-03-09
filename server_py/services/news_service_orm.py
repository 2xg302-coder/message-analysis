from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import difflib
import re
from simhash import Simhash
from sqlmodel import select, col
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from models_orm import News, Watchlist
from core.database_orm import engine
from sqlalchemy.orm import sessionmaker

class NewsServiceORM:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        if self.session:
            return self.session
        # Create a new session if not provided (for standalone usage)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return async_session()

    def _prepare_news_item(self, item: Dict[str, Any]) -> News:
        # Convert dict to News model, handling JSON fields
        news = News(**item)
        if isinstance(item.get('tags'), list):
            news.tags = json.dumps(item['tags'], ensure_ascii=False)
        if isinstance(item.get('entities'), dict):
            news.entities = json.dumps(item['entities'], ensure_ascii=False)
        if isinstance(item.get('analysis'), (dict, list)):
            news.analysis = json.dumps(item['analysis'], ensure_ascii=False)
        
        # Ensure created_at
        if not news.created_at:
            news.created_at = datetime.now().isoformat()
            
        return news

    def _process_result(self, news: News) -> Dict[str, Any]:
        # Convert News model back to dict with parsed JSON
        item = news.dict()
        try:
            item['tags'] = json.loads(item['tags']) if item['tags'] else []
        except: item['tags'] = []
            
        try:
            item['entities'] = json.loads(item['entities']) if item['entities'] else {}
        except: item['entities'] = {}
            
        try:
            item['analysis'] = json.loads(item['analysis']) if item['analysis'] else None
        except: item['analysis'] = None
            
        return item

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

    async def add_news(self, news_item: Dict[str, Any]) -> bool:
        session = await self._get_session()
        try:
            # Check existence
            stmt = select(News).where(News.id == news_item['id'])
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return False

            news = self._prepare_news_item(news_item)
            session.add(news)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            return False
        finally:
            if not self.session:
                await session.close()

    async def add_news_batch(self, news_list: List[Dict[str, Any]]) -> int:
        if not news_list:
            return 0
            
        session = await self._get_session()
        count = 0
        try:
            for item in news_list:
                # Check existence (batch check could be optimized)
                stmt = select(News.id).where(News.id == item['id'])
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    news = self._prepare_news_item(item)
                    session.add(news)
                    count += 1
            
            await session.commit()
            return count
        except Exception as e:
            await session.rollback()
            return 0
        finally:
            if not self.session:
                await session.close()

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
        
        session = await self._get_session()
        try:
            # Build filters
            filters = []
            
            if news_type:
                filters.append(News.type == news_type)
            
            if min_impact is not None:
                filters.append(News.impact_score >= min_impact)
            
            if source:
                filters.append(News.source == source)
                
            if tag:
                # SQLite JSON specific search or string search
                filters.append(col(News.tags).contains(tag))

            if sentiment:
                if sentiment == 'positive':
                    filters.append(News.sentiment_score > 0.05)
                elif sentiment == 'negative':
                    filters.append(News.sentiment_score < -0.05)
                elif sentiment == 'neutral':
                    filters.append(News.sentiment_score >= -0.05)
                    filters.append(News.sentiment_score <= 0.05)

            if keyword:
                # Search in title, content, or entities
                # entities is stored as JSON string, so contains works
                filters.append(
                    (News.title.contains(keyword)) | 
                    (News.content.contains(keyword)) | 
                    (col(News.entities).contains(keyword))
                )
                
            if start_date and end_date:
                # Assuming created_at is ISO string, string comparison works for YYYY-MM-DD
                filters.append(News.created_at >= start_date)
                filters.append(News.created_at <= end_date + "T23:59:59.999999")

            # 1. Get Data
            stmt = select(News).order_by(News.created_at.desc()).offset(offset).limit(limit)
            if filters:
                stmt = stmt.where(*filters)

            result = await session.execute(stmt)
            news_list = result.scalars().all()
            processed_list = [self._process_result(news) for news in news_list]
            
            if not return_total:
                return processed_list

            # 2. Get Total Count
            stmt_count = select(func.count(News.id))
            if filters:
                stmt_count = stmt_count.where(*filters)
            
            total = await session.scalar(stmt_count)
            
            return processed_list, (total or 0)

        finally:
            if not self.session:
                await session.close()

    async def get_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None, exclude_source: Optional[str] = None) -> Dict[str, Any]:
        session = await self._get_session()
        try:
            # Base filters
            filters = []
            source_filters = []
            if start_date and end_date:
                filters.append(News.created_at >= start_date)
                filters.append(News.created_at <= end_date)
            if exclude_source:
                filters.append(News.source != exclude_source)
                source_filters.append(News.source != exclude_source)

            # Total count
            stmt_total = select(func.count(News.id))
            if filters:
                stmt_total = stmt_total.where(*filters)
            total = await session.scalar(stmt_total)
            
            # Analyzed count
            stmt_analyzed = select(func.count(News.id)).where(News.analysis.is_not(None))
            if filters:
                stmt_analyzed = stmt_analyzed.where(*filters)
            analyzed = await session.scalar(stmt_analyzed)
            
            created_date_hour_expression = func.substr(News.created_at, 1, 13)
            created_hour_expression = func.substr(News.created_at, 12, 2)
            analyzed_date_hour_expression = func.substr(News.analyzed_at, 1, 13)
            analyzed_hour_expression = func.substr(News.analyzed_at, 12, 2)

            collection_trend_filters = list(source_filters)
            analyzed_trend_filters = [*source_filters, News.analyzed_at.is_not(None), News.analysis.is_not(None), News.analysis != ""]
            if not start_date and not end_date:
                current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
                cutoff = (current_hour - timedelta(hours=23)).isoformat()
                collection_trend_filters.append(News.created_at >= cutoff)
                analyzed_trend_filters.append(News.analyzed_at >= cutoff)
            else:
                current_hour = None
                collection_trend_filters.append(News.created_at >= start_date)
                collection_trend_filters.append(News.created_at <= end_date)
                analyzed_trend_filters.append(News.analyzed_at >= start_date)
                analyzed_trend_filters.append(News.analyzed_at <= end_date + "T23:59:59.999999")

            stmt_collection_trends = select(
                created_date_hour_expression.label("date_hour"),
                created_hour_expression.label("hour"),
                func.count(News.id).label("count")
            )
            if collection_trend_filters:
                stmt_collection_trends = stmt_collection_trends.where(*collection_trend_filters)
            stmt_collection_trends = stmt_collection_trends.group_by(created_date_hour_expression, created_hour_expression).order_by(created_date_hour_expression.asc())
            collection_trends_res = await session.execute(stmt_collection_trends)
            collection_rows = collection_trends_res.all()

            stmt_analyzed_trends = select(
                analyzed_date_hour_expression.label("date_hour"),
                analyzed_hour_expression.label("hour"),
                func.count(News.id).label("analyzed_count")
            )
            if analyzed_trend_filters:
                stmt_analyzed_trends = stmt_analyzed_trends.where(*analyzed_trend_filters)
            stmt_analyzed_trends = stmt_analyzed_trends.group_by(analyzed_date_hour_expression, analyzed_hour_expression).order_by(analyzed_date_hour_expression.asc())
            analyzed_trends_res = await session.execute(stmt_analyzed_trends)
            analyzed_rows = analyzed_trends_res.all()

            if current_hour:
                collection_map = {row.date_hour: row.count or 0 for row in collection_rows}
                analyzed_map = {row.date_hour: row.analyzed_count or 0 for row in analyzed_rows}
                trends = []
                for i in range(23, -1, -1):
                    t = current_hour - timedelta(hours=i)
                    key = t.strftime("%Y-%m-%dT%H")
                    trends.append({
                        "hour": t.strftime("%H:00"),
                        "count": collection_map.get(key, 0),
                        "analyzed_count": analyzed_map.get(key, 0)
                    })
            else:
                merged_map = {}
                for row in collection_rows:
                    merged_map[row.date_hour] = {
                        "hour": f"{row.hour}:00",
                        "count": row.count or 0,
                        "analyzed_count": 0
                    }
                for row in analyzed_rows:
                    if row.date_hour not in merged_map:
                        merged_map[row.date_hour] = {
                            "hour": f"{row.hour}:00",
                            "count": 0,
                            "analyzed_count": row.analyzed_count or 0
                        }
                    else:
                        merged_map[row.date_hour]["analyzed_count"] = row.analyzed_count or 0
                trends = [merged_map[k] for k in sorted(merged_map.keys())]
            
            return {
                "total": total or 0,
                "analyzed": analyzed or 0,
                "pending": (total or 0) - (analyzed or 0),
                "trends": trends
            }
        finally:
            if not self.session:
                await session.close()

    async def get_tag_stats(self, limit: int = 100, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            # Optimized logic: fetch only tags column
            stmt = select(News.tags).where(News.tags.is_not(None)).where(News.tags != "[]")
            
            if start_date and end_date:
                stmt = stmt.where(News.created_at >= start_date).where(News.created_at <= end_date)
                row_limit = 50000
            else:
                row_limit = 5000
                
            stmt = stmt.order_by(News.created_at.desc()).limit(row_limit)
            
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            from collections import Counter
            tag_counts = Counter()
            
            for tags_json in rows:
                try:
                    tags = json.loads(tags_json)
                    if isinstance(tags, list):
                        tag_counts.update(tags)
                except: pass
                
            return [{"name": name, "value": count} for name, count in tag_counts.most_common(limit)]
        finally:
            if not self.session:
                await session.close()

    async def get_type_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            stmt = select(News.analysis).where(News.analysis.is_not(None))
            
            if start_date and end_date:
                stmt = stmt.where(News.created_at >= start_date).where(News.created_at <= end_date)
            
            stmt = stmt.order_by(News.created_at.desc()).limit(2000)
            
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            type_counts = {}
            for analysis_json in rows:
                try:
                    analysis = json.loads(analysis_json)
                    if isinstance(analysis, dict):
                        etype = analysis.get('event_type', '其他')
                        type_counts[etype] = type_counts.get(etype, 0) + 1
                except: pass
                
            return [{"name": name, "value": count} for name, count in type_counts.items()]
        finally:
            if not self.session:
                await session.close()

    async def get_top_entities(self, limit: int = 50, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            stmt = select(News.entities).where(News.entities.is_not(None))
            if start_date and end_date:
                stmt = stmt.where(News.created_at >= start_date).where(News.created_at <= end_date)
            
            stmt = stmt.order_by(News.created_at.desc()).limit(1000)
            
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            entity_counts = {}
            for ent_json in rows:
                try:
                    ents = json.loads(ent_json)
                    if isinstance(ents, dict):
                        for name, _ in ents.items():
                            entity_counts[name] = entity_counts.get(name, 0) + 1
                except: pass
                
            sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"name": name, "count": count} for name, count in sorted_entities]
        finally:
            if not self.session:
                await session.close()

    async def get_series_list(self) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            # Using LIKE for simple text search in JSON string
            stmt = select(News.analysis, News.created_at).where(News.analysis.is_not(None)).where(col(News.analysis).contains('"event_tag"'))
            stmt = stmt.order_by(News.created_at.desc()).limit(2000)
            
            result = await session.execute(stmt)
            rows = result.all() # tuples of (analysis, created_at)
            
            series_map = {}
            for analysis_json, created_at in rows:
                try:
                    analysis = json.loads(analysis_json)
                    tag = analysis.get('event_tag')
                    if tag:
                        if tag not in series_map:
                            series_map[tag] = {
                                'tag': tag,
                                'count': 0,
                                'latest_date': created_at,
                                'sample_summary': analysis.get('summary')
                            }
                        series_map[tag]['count'] += 1
                except: pass
                
            return sorted(series_map.values(), key=lambda x: x['latest_date'], reverse=True)
        finally:
            if not self.session:
                await session.close()

    async def get_news_by_series(self, tag: str) -> List[Dict[str, Any]]:
        session = await self._get_session()
        try:
            # Search for tag in analysis field
            # Ideally we should use JSON operators but for compatibility we use string contains
            stmt = select(News).where(col(News.analysis).contains(tag)).order_by(News.created_at.desc())
            
            result = await session.execute(stmt)
            news_list = result.scalars().all()
            
            final_list = []
            for news in news_list:
                item = self._process_result(news)
                # Double check in python because string match might be partial
                if item.get('analysis', {}).get('event_tag') == tag:
                    final_list.append(item)
            return final_list
        finally:
            if not self.session:
                await session.close()

    async def scan_cross_source_duplicates(
        self,
        lookback_hours: int = 24,
        limit: int = 300,
        distance_threshold: int = 6,
        min_text_len: int = 20
    ) -> Dict[str, Any]:
        session = await self._get_session()
        try:
            since = (datetime.now() - timedelta(hours=max(1, lookback_hours))).isoformat()
            capped_limit = max(10, min(limit, 1000))
            stmt = (
                select(News.id, News.source, News.title, News.content, News.created_at, News.simhash)
                .where(News.created_at >= since)
                .order_by(News.created_at.desc())
                .limit(capped_limit)
            )
            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return {
                    "total_candidates": 0,
                    "pairs_count": 0,
                    "pairs": [],
                    "recommended_delete_ids": []
                }

            candidates: List[Dict[str, Any]] = []
            for row in rows:
                item = {
                    "id": row.id,
                    "source": row.source,
                    "title": row.title,
                    "content": row.content,
                    "created_at": row.created_at,
                    "simhash": row.simhash
                }
                raw_text = item.get("content") or item.get("title") or ""
                text = self._normalize_for_simhash(raw_text)
                compare_text = self._normalize_for_compare(raw_text)
                if len(compare_text) < min_text_len:
                    continue

                sh = None
                if item.get("simhash") not in (None, ""):
                    try:
                        sh = Simhash(int(str(item["simhash"])))
                    except Exception:
                        sh = None
                if sh is None:
                    try:
                        sh = Simhash(text)
                    except Exception:
                        continue

                item["_clean_text"] = text
                item["_compare_text"] = compare_text
                item["_simhash_obj"] = sh
                candidates.append(item)

            pairs: List[Dict[str, Any]] = []
            recommended_delete_ids = set()
            seen_pair_keys = set()

            for i in range(len(candidates)):
                left = candidates[i]
                for j in range(i + 1, len(candidates)):
                    right = candidates[j]
                    if left.get("source") == right.get("source"):
                        continue

                    distance = left["_simhash_obj"].distance(right["_simhash_obj"])
                    similar = distance <= distance_threshold
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
        finally:
            if not self.session:
                await session.close()

    async def delete_news_batch(self, news_ids: List[str]) -> int:
        clean_ids = [nid for nid in news_ids if nid]
        if not clean_ids:
            return 0
        session = await self._get_session()
        try:
            from sqlalchemy import delete
            stmt = delete(News).where(News.id.in_(clean_ids))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount or 0
        except Exception:
            await session.rollback()
            return 0
        finally:
            if not self.session:
                await session.close()

    async def get_watchlist(self) -> List[str]:
        session = await self._get_session()
        try:
            stmt = select(Watchlist.keyword).order_by(Watchlist.created_at.asc())
            result = await session.execute(stmt)
            return result.scalars().all()
        finally:
            if not self.session:
                await session.close()

    async def update_watchlist(self, keywords: List[str]) -> bool:
        session = await self._get_session()
        try:
            # Delete all
            # SQLModel doesn't have a direct delete all without where, but verify
            from sqlalchemy import delete
            await session.execute(delete(Watchlist))
            
            # Insert new
            current_time = datetime.now().isoformat()
            for kw in keywords:
                wl = Watchlist(keyword=kw, created_at=current_time)
                session.add(wl)
            
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            return False
        finally:
            if not self.session:
                await session.close()
