import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from simhash import Simhash
from flashtext import KeywordProcessor
import akshare as ak
from services.news_service import news_service
from services.vector_store import vector_store
import os
import logging
import asyncio

logger = logging.getLogger("processor")

class NewsProcessor:
    def __init__(self):
        self.keyword_processor = KeywordProcessor()
        self.simhash_cache: List[Dict[str, Any]] = [] # {simhash, time, id, text}
        self.watchlist_keywords = []
        self.last_watchlist_update = datetime.min
        self.expected_events: Dict[str, List[Dict[str, Any]]] = {}
        self.load_expected_events()
        self.rules = {
            "立案调查": {"score": 5, "sentiment": -0.8, "tags": ["监管", "立案"]},
            "业绩预增": {"score": 4, "sentiment": 0.6, "tags": ["业绩"]},
            "涨停": {"score": 3, "sentiment": 0.5, "tags": ["行情"]},
            "跌停": {"score": 3, "sentiment": -0.5, "tags": ["行情"]},
            "收购": {"score": 4, "sentiment": 0.2, "tags": ["并购"]},
            "减持": {"score": 3, "sentiment": -0.3, "tags": ["人事"]},
            "增持": {"score": 3, "sentiment": 0.3, "tags": ["人事"]},
            "加息": {"score": 5, "sentiment": -0.3, "tags": ["宏观", "货币政策"]},
            "降息": {"score": 5, "sentiment": 0.4, "tags": ["宏观", "货币政策"]},
            "黄金": {"score": 3, "sentiment": 0.1, "tags": ["大宗商品"]},
            "战争": {"score": 5, "sentiment": -0.5, "tags": ["地缘政治"]},
            "冲突": {"score": 4, "sentiment": -0.4, "tags": ["地缘政治"]},
            "传闻": {"score": 2, "sentiment": 0.0, "tags": ["市场传闻"]},
            "小作文": {"score": 2, "sentiment": 0.0, "tags": ["市场传闻"]},
        }
        self.load_keywords()
        # self.load_recent_hashes() # Moved to init_async

    def load_expected_events(self):
        try:
            # Try loading from server_py/data/expected_events.json
            # Correct path relative to services/processor.py -> ../data/expected_events.json
            path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'expected_events.json'))
            
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.expected_events = json.load(f)
                # logger.info(f"Loaded expected events for {len(self.expected_events)} days.")
            else:
                logger.warning(f"Expected events file not found at {path}")
        except Exception as e:
            logger.error(f"Error loading expected events: {e}")

    def load_recent_hashes(self):
        # Sync method kept for compatibility, but logic moved to init_async
        pass
            
    async def init_async(self):
        logger.info("Loading recent news for deduplication (Async)...")
        try:
            # Load Watchlist
            try:
                self.watchlist_keywords = await news_service.get_watchlist()
                logger.info(f"Loaded {len(self.watchlist_keywords)} watchlist keywords.")
            except Exception as e:
                logger.error(f"Error loading watchlist: {e}")

            recent_news = await news_service.get_news(limit=1000)
            count = 0
            for item in recent_news:
                # Need valid ID to enable deletion logic
                if 'id' not in item:
                    continue
                    
                # Compute clean text for containment check
                raw_content = item.get('content', '') or item.get('title', '')
                clean_content = self.clean_text(raw_content)
                
                # Use existing simhash or recompute
                sh = None
                if 'simhash' in item and item['simhash']:
                    try:
                        sh = Simhash(item['simhash'])
                    except:
                        pass
                
                if not sh and clean_content:
                    sh = self.calculate_simhash(clean_content)
                
                if sh:
                    t_str = item.get('created_at') or item.get('scrapedAt')
                    if t_str:
                        try:
                            t = datetime.fromisoformat(t_str)
                            self.simhash_cache.append({
                                'hash': sh, 
                                'time': t,
                                'id': item['id'],
                                'text': clean_content
                            })
                            count += 1
                        except:
                            pass
            
            logger.info(f"Loaded {count} items into deduplication cache.")
        except Exception as e:
            logger.error(f"Error loading recent hashes: {e}")

    def load_keywords(self):
        # logger.info("Loading keywords for NER...")
        try:
            try:
                stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
                for _, row in stock_zh_a_spot_em_df.iterrows():
                    name = row['名称']
                    code = row['代码']
                    self.keyword_processor.add_keyword(name, {"name": name, "code": code, "type": "A_SHARE"})
                    self.keyword_processor.add_keyword(code, {"name": name, "code": code, "type": "A_SHARE"})
                logger.info(f"Loaded {len(self.keyword_processor)} keywords from EastMoney.")
            except Exception as e:
                logger.warning(f"Failed to load real-time stock list: {e}")
                common_entities = [
                    "贵州茅台", "宁德时代", "腾讯", "阿里巴巴", "美团", "比亚迪", "京东", "百度", "拼多多",
                    "中芯国际", "中国平安", "招商银行", "工商银行", "中国移动", "中国石油", "中国海油",
                    "华为", "小米", "OpenAI", "DeepSeek", "特斯拉", "英伟达", "微软", "谷歌", "苹果",
                    "证监会", "央行", "美联储"
                ]
                for name in common_entities:
                    self.keyword_processor.add_keyword(name, {"name": name, "code": "", "type": "KEYWORD"})
            
        except Exception as e:
            logger.error(f"Error loading keywords: {e}")

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove standard disclaimers
        text = re.sub(r'【免责声明】.*', '', text)
        # Remove reporter info
        text = re.sub(r'（记者\s+.*?）', '', text)
        text = re.sub(r'\(记者\s+.*?\)', '', text)
        
        # Remove source prefixes like "财联社3月6日电，" or "财联社3月6日讯，"
        # Pattern: 2-6 chars (source) + date + 电/讯 + comma/space
        text = re.sub(r'^.{2,6}\d{1,2}月\d{1,2}日[电讯][，,]', '', text)
        
        # Remove bracketed titles at start if they look like summaries
        # e.g. 【Title】Content...
        text = re.sub(r'^【.*?】', '', text)
        
        return text.strip()

    def calculate_simhash(self, text: str) -> Simhash:
        return Simhash(text)

    def is_duplicate(self, current_simhash: Simhash, current_text: str, current_time: datetime) -> Tuple[bool, List[str]]:
        """
        Check if duplicate.
        Returns: (is_duplicate_new, ids_to_delete)
        """
        cutoff = current_time - timedelta(hours=24)
        self.simhash_cache = [x for x in self.simhash_cache if x['time'] > cutoff]
        
        ids_to_delete = []
        is_dupe = False
        
        for item in self.simhash_cache:
            # 1. SimHash Distance Check
            distance = current_simhash.distance(item['hash'])
            if distance <= 3:
                # Found a very similar item.
                # Usually we discard the new one.
                is_dupe = True
                # But check if new one is significantly longer/better?
                # For now, stick to simple SimHash logic: first come first serve.
                break
            
            # 2. Containment Check
            cached_text = item.get('text', '')
            if not cached_text or not current_text:
                continue
                
            # If new text is contained in old text (and old text is longer) -> New is duplicate
            if len(current_text) < len(cached_text) and current_text in cached_text:
                is_dupe = True
                break
                
            # If old text is contained in new text (and new text is longer) -> Old is duplicate (delete old)
            if len(cached_text) < len(current_text) and cached_text in current_text:
                # Mark old for deletion, but keep checking other items
                # We don't set is_dupe = True here because we want to keep the new one
                if item.get('id'):
                    ids_to_delete.append(item['id'])
        
        return is_dupe, ids_to_delete

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        keywords_found = self.keyword_processor.extract_keywords(text)
        return keywords_found

    def match_expected_events(self, content: str, news_time: datetime = None) -> List[Dict[str, Any]]:
        if not news_time:
            news_time = datetime.now()
        
        date_str = news_time.strftime('%Y-%m-%d')
        if date_str not in self.expected_events:
            return []
            
        matches = []
        events = self.expected_events[date_str]
        
        for event in events:
            event_name = event.get('event', '')
            if not event_name:
                continue
                
            if event_name in content:
                matches.append(event)
                continue
                
            country = event.get('country', '')
            if country and country in content:
                key_term = event_name.replace("年率", "").replace("月率", "").replace("季调", "").replace("未", "")
                if len(key_term) > 1 and key_term in content:
                    matches.append(event)

        return matches

    def rate_news(self, text: str) -> Dict[str, Any]:
        score = 0
        sentiment = 0.0
        matched_rules = []
        tags = set()
        
        for keyword, rule in self.rules.items():
            if keyword in text:
                score += rule['score']
                sentiment += rule['sentiment']
                matched_rules.append(keyword)
                if 'tags' in rule:
                    for t in rule['tags']:
                        tags.add(t)
        
        if matched_rules:
            sentiment = sentiment / len(matched_rules)
            
        return {
            "impact_score": min(score, 10), 
            "sentiment": max(min(sentiment, 1.0), -1.0), 
            "matched_rules": matched_rules,
            "tags": list(tags)
        }

    async def process(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Refresh Watchlist periodically (e.g., every 60s)
        if (datetime.now() - self.last_watchlist_update).total_seconds() > 60:
            try:
                self.watchlist_keywords = await news_service.get_watchlist()
                self.last_watchlist_update = datetime.now()
                # logger.debug(f"Refreshed watchlist: {len(self.watchlist_keywords)} keywords")
            except Exception as e:
                logger.warning(f"Failed to refresh watchlist: {e}")

        raw_content = news_item.get('content', '') or news_item.get('title', '')
        if not raw_content:
            return None
            
        clean_content = self.clean_text(raw_content)
        news_item['clean_content'] = clean_content
        
        current_time = datetime.now()
        simhash = self.calculate_simhash(clean_content)
        
        if len(clean_content) > 10: # Lowered threshold slightly
            is_dupe, ids_to_delete = self.is_duplicate(simhash, clean_content, current_time)
            
            if ids_to_delete:
                logger.info(f"Found {len(ids_to_delete)} inferior duplicates to delete.")
                for old_id in ids_to_delete:
                    await news_service.delete_news(old_id)
                    # Also remove from cache
                    self.simhash_cache = [x for x in self.simhash_cache if x.get('id') != old_id]
            
            if is_dupe:
                logger.info(f"Duplicate detected: {clean_content[:20]}...")
                return None
            
        self.simhash_cache.append({
            'hash': simhash, 
            'time': current_time,
            'id': news_item.get('id'),
            'text': clean_content
        })
        news_item['simhash'] = simhash.value
        
        entities = self.extract_entities(clean_content)
        news_item['entities'] = entities
        
        rating = self.rate_news(clean_content)
        news_item['rating'] = rating
        news_item['tags'] = rating.get('matched_rules', []) + rating.get('tags', [])

        # Match Watchlist
        content_to_check = (news_item.get('title', '') + ' ' + clean_content).lower()
        for kw in self.watchlist_keywords:
            if kw.lower() in content_to_check:
                if '关注' not in news_item['tags']:
                    news_item['tags'].append('关注')
                # Boost impact score
                news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 2, 10)
                break
        
        item_time = None
        if 'time' in news_item:
             try:
                 item_time = datetime.strptime(news_item['time'], '%Y-%m-%d %H:%M:%S')
             except:
                 pass
        
        expected_matches = self.match_expected_events(clean_content, item_time)
        if expected_matches:
            news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 3, 10)
            
            for event in expected_matches:
                tag = f"预期:{event['country']}{event['event']}"
                if tag not in news_item['tags']:
                    news_item['tags'].append(tag)
            
            news_item['expected_events'] = expected_matches

        # Semantic Match Storylines
        # Only perform semantic matching if content is sufficient length
        if clean_content and len(clean_content) > 20:
            try:
                # Use a slightly higher threshold to ensure quality (e.g. 0.45 cosine similarity)
                matches = await vector_store.query_news_tags(clean_content, threshold=0.45)
                
                if matches:
                    matched_tags = []
                    
                    # Boost score if matched storyline
                    # Base boost for any match
                    news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 1, 10)
                    
                    for m in matches:
                        tag = f"主线:{m['title']}"
                        matched_tags.append(tag)
                        
                        # Extra boost for high confidence match
                        if m['score'] > 0.6:
                             news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 1, 10)

                    # Add to tags
                    if 'tags' not in news_item:
                        news_item['tags'] = []
                    
                    for tag in matched_tags:
                        if tag not in news_item['tags']:
                            news_item['tags'].append(tag)
                            
                    # Add detailed match info
                    news_item['storyline_matches'] = matches
                    
            except Exception as e:
                logger.error(f"Error in semantic matching: {e}")

        return news_item
