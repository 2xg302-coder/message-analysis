import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from simhash import Simhash
from flashtext import KeywordProcessor
from difflib import SequenceMatcher
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
        self.blocklist_keywords = []
        self.last_watchlist_update = datetime.min
        self.last_blocklist_update = datetime.min
        self.expected_events: Dict[str, List[Dict[str, Any]]] = {}
        self.load_expected_events()
        self.rules = {
            # 高分项 (5分): 重大政策、监管、宏观
            "立案调查": {"score": 5, "sentiment": -0.8, "tags": ["监管", "立案"]},
            "加息": {"score": 5, "sentiment": -0.3, "tags": ["宏观", "货币政策"]},
            "降息": {"score": 5, "sentiment": 0.4, "tags": ["宏观", "货币政策"]},
            "战争": {"score": 5, "sentiment": -0.5, "tags": ["地缘政治"]},
            "降准": {"score": 5, "sentiment": 0.4, "tags": ["宏观", "货币政策"]},
            "印花税": {"score": 5, "sentiment": 0.3, "tags": ["政策", "股市"]},
            "暂停IPO": {"score": 5, "sentiment": 0.6, "tags": ["政策", "IPO"]},
            "退市": {"score": 5, "sentiment": -0.6, "tags": ["监管", "退市"]},
            
            # 中高分项 (4分): 行业大事、公司大事
            "业绩预增": {"score": 4, "sentiment": 0.6, "tags": ["业绩"]},
            "收购": {"score": 4, "sentiment": 0.2, "tags": ["并购"]},
            "冲突": {"score": 4, "sentiment": -0.4, "tags": ["地缘政治"]},
            "首发": {"score": 4, "sentiment": 0.3, "tags": ["新品"]},
            "突破": {"score": 4, "sentiment": 0.5, "tags": ["技术"]},
            "获批": {"score": 4, "sentiment": 0.5, "tags": ["政策", "利好"]},
            "中标": {"score": 4, "sentiment": 0.4, "tags": ["合同"]},
            "回购": {"score": 4, "sentiment": 0.5, "tags": ["回购"]},
            "举牌": {"score": 4, "sentiment": 0.4, "tags": ["股权"]},
            "违约": {"score": 4, "sentiment": -0.7, "tags": ["风险"]},
            "暴雷": {"score": 4, "sentiment": -0.8, "tags": ["风险"]},
            "制裁": {"score": 4, "sentiment": -0.6, "tags": ["贸易"]},
            "关税": {"score": 4, "sentiment": -0.4, "tags": ["贸易"]},
            
            # 普通项 (3分): 市场波动、常规动态
            "涨停": {"score": 3, "sentiment": 0.5, "tags": ["行情"]},
            "跌停": {"score": 3, "sentiment": -0.5, "tags": ["行情"]},
            "减持": {"score": 3, "sentiment": -0.3, "tags": ["人事"]},
            "增持": {"score": 3, "sentiment": 0.3, "tags": ["人事"]},
            "黄金": {"score": 3, "sentiment": 0.1, "tags": ["大宗商品"]},
            "原油": {"score": 3, "sentiment": 0.1, "tags": ["大宗商品"]},
            "大涨": {"score": 3, "sentiment": 0.4, "tags": ["行情"]},
            "大跌": {"score": 3, "sentiment": -0.4, "tags": ["行情"]},
            "新高": {"score": 3, "sentiment": 0.4, "tags": ["行情"]},
            "新低": {"score": 3, "sentiment": -0.4, "tags": ["行情"]},
            "发布": {"score": 3, "sentiment": 0.1, "tags": ["动态"]},
            "合作": {"score": 3, "sentiment": 0.2, "tags": ["合作"]},
            "签署": {"score": 3, "sentiment": 0.2, "tags": ["合作"]},
            
            # 低分项 (2分): 传闻、噪音
            "传闻": {"score": 2, "sentiment": 0.0, "tags": ["市场传闻"]},
            "小作文": {"score": 2, "sentiment": 0.0, "tags": ["市场传闻"]},
            "回应": {"score": 2, "sentiment": 0.0, "tags": ["回应"]},
            "澄清": {"score": 2, "sentiment": 0.1, "tags": ["回应"]},
        }
        # self.load_keywords() # Moved to init_async to avoid blocking startup
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
        logger.info("Initializing processor (Async)...")
        
        # Load keywords in background thread to avoid blocking loop
        try:
            await asyncio.to_thread(self.load_keywords)
        except Exception as e:
            logger.error(f"Error loading keywords async: {e}")

        logger.info("Loading recent news for deduplication (Async)...")
        try:
            # Load Watchlist
            try:
                self.watchlist_keywords = await news_service.get_watchlist()
                logger.info(f"Loaded {len(self.watchlist_keywords)} watchlist keywords.")
            except Exception as e:
                logger.error(f"Error loading watchlist: {e}")

            # Load Blocklist
            try:
                self.blocklist_keywords = await news_service.get_blocklist()
                logger.info(f"Loaded {len(self.blocklist_keywords)} blocklist keywords.")
            except Exception as e:
                logger.error(f"Error loading blocklist: {e}")

            recent_news = await news_service.get_news(limit=1000)
            count = 0
            for item in recent_news:
                # Need valid ID to enable deletion logic
                if 'id' not in item:
                    continue
                    
                # Compute clean text for containment check
                raw_content = item.get('content', '') or item.get('title', '')
                clean_content = self.clean_text(raw_content)
                clean_title = self.clean_title(item.get('title', ''))
                
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
                                'text': clean_content,
                                'title': clean_title,
                                'source': item.get('source')
                            })
                            count += 1
                        except:
                            pass
            
            logger.info(f"Loaded {count} items into deduplication cache.")
        except Exception as e:
            logger.error(f"Error loading recent hashes: {e}")

    def load_keywords(self):
        # logger.info("Loading keywords for NER...")
        cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'stock_keywords_cache.json'))
        loaded = False
        
        try:
            # 1. Try loading from cache
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        updated_at = datetime.fromisoformat(cache_data.get('updated_at', '2000-01-01'))
                        
                        # Cache valid for 24 hours
                        if (datetime.now() - updated_at).total_seconds() < 86400:
                            keywords_list = cache_data.get('data', [])
                            for item in keywords_list:
                                self.keyword_processor.add_keyword(item['name'], item)
                                self.keyword_processor.add_keyword(item['code'], item)
                            logger.info(f"Loaded {len(keywords_list)} keywords from local cache.")
                            loaded = True
                except Exception as e:
                    logger.warning(f"Failed to load keywords cache: {e}")

            if loaded:
                return

            try:
                stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
                cache_list = []
                for _, row in stock_zh_a_spot_em_df.iterrows():
                    name = row['名称']
                    code = row['代码']
                    meta = {"name": name, "code": code, "type": "A_SHARE"}
                    self.keyword_processor.add_keyword(name, meta)
                    self.keyword_processor.add_keyword(code, meta)
                    cache_list.append(meta)
                logger.info(f"Loaded {len(self.keyword_processor)} keywords from EastMoney.")
                
                # Save to cache
                try:
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            "updated_at": datetime.now().isoformat(),
                            "data": cache_list
                        }, f, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"Failed to save keywords cache: {e}")

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

    def clean_text(self, text: str, source: str = None) -> str:
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
        
        if source == 'ITHome':
            text = self.clean_ithome_text(text)
            
        return text.strip()

    def clean_ithome_text(self, text: str) -> str:
        """Specific cleaning for ITHome content"""
        if not text:
            return ""
        
        # Common ITHome ad patterns
        patterns = [
            r'广告声明：.*',
            r'IT之家.*?日消息，', # Remove header like "IT之家 3 月 8 日消息，"
            r'京东.*?直达链接',
            r'天猫.*?直达链接',
            r'淘宝.*?直达链接',
            r'\[.*?\]', # Remove [Product Name] etc
            r'【.*?】',  # Remove 【Product Name】 etc
        ]
        
        cleaned = text
        for p in patterns:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
            
        # Remove specific promotional phrases
        promo_phrases = [
            "点击此处", "购买链接", "直达链接", "一键直达", 
            "领券", "大额券", "折合", "到手价", "包邮", 
            "晒单", "返现", "限量", "秒杀"
        ]
        
        for phrase in promo_phrases:
            cleaned = cleaned.replace(phrase, "")
            
        return cleaned.strip()

    def filter_yonhap_news(self, news_item: Dict[str, Any]) -> bool:
        """
        Filter Yonhap news to keep only:
        - Politics (All)
        - Major Economy (Filtered by keywords)
        - North Korea related (All)
        """
        title = news_item.get('title', '')
        content = news_item.get('content', '') or ''
        category = news_item.get('raw_tags', '') # Set in collector
        
        text = (title + " " + content).lower()
        
        # 1. North Korea Related (Highest Priority - Keep from any category)
        nk_keywords = [
            "朝鲜", "北韩", "金正恩", "金与正", "平壤", "劳动党", "人民军", 
            "核试验", "导弹", "发射", "挑衅", "非军事区", "板门店", "开城", 
            "统一部", "脱北", "朝方", "韩朝", "朝韩", "军事分界线"
        ]
        if any(k in text for k in nk_keywords):
            return True
            
        # 2. Politics
        # If category is explicitly politics, keep it.
        if category == 'politics':
            return True
            
        # Also check keywords for politics in other categories
        politics_keywords = [
            "总统", "尹锡悦", "国会", "执政党", "在野党", "国民力量", "共同民主党", 
            "选举", "青瓦台", "龙山", "外交部", "国防部", "韩美", "韩中", "韩日", 
            "峰会", "会谈", "大使", "长官", "总理"
        ]
        if any(k in text for k in politics_keywords):
            return True
            
        # 3. Major Economy
        # Keywords for major economic events
        economy_keywords = [
            "gdp", "增长率", "央行", "利率", "基准利率", "通胀", "物价", "cpi", "ppi", 
            "出口", "进口", "贸易收支", "半导体", "芯片", "三星电子", "sk海力士", "现代汽车", 
            "电池", "汇率", "韩元", "kospi", "kosdaq", "预算", "财政", "失业率", "就业",
            "自由贸易协定", "fta"
        ]
        
        # If category is economy, we still filter by keywords to ensure "Major"
        # Or should we be more lenient for 'economy' category?
        # User said "只关注重大经济", so filtering is safer.
        if any(k in text for k in economy_keywords):
            return True
            
        return False

    def clean_title(self, text: str) -> str:
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

    def calculate_simhash(self, text: str) -> Simhash:
        return Simhash(text)

    def is_duplicate(self, current_simhash: Simhash, current_text: str, current_title: str, current_time: datetime, current_source: str = None) -> Tuple[bool, List[str]]:
        """
        Check if duplicate.
        Returns: (is_duplicate_new, ids_to_delete)
        """
        cutoff = current_time - timedelta(hours=24)
        self.simhash_cache = [x for x in self.simhash_cache if x['time'] > cutoff]
        
        ids_to_delete = set()
        is_dupe = False
        
        for item in self.simhash_cache:
            # Check source and time for stricter/relaxed logic
            same_source = current_source and item.get('source') == current_source
            # If item['time'] is timezone aware and current_time is naive (or vice versa), this might fail.
            # Assuming both are either naive or aware.
            try:
                time_diff = abs((current_time - item['time']).total_seconds())
            except:
                time_diff = 999999

            # 1. SimHash Distance Check (Content)
            distance = current_simhash.distance(item['hash'])
            threshold = 3
            if same_source and time_diff < 300: # 5 mins
                threshold = 6 # Relaxed threshold for same source & time

            if distance <= threshold:
                is_dupe = True
                break
            
            # 2. Content Containment Check
            cached_text = item.get('text', '')
            if cached_text and current_text:
                if len(current_text) < len(cached_text) and current_text in cached_text:
                    is_dupe = True
                    break
                if len(cached_text) < len(current_text) and cached_text in current_text:
                    # We don't set is_dupe = True here because we want to keep the new one
                    if item.get('id'):
                        ids_to_delete.add(item['id'])
            
            # 3. Title Check
            cached_title = item.get('title', '')
            if cached_title and current_title:
                # 3a. Title Containment
                if len(current_title) > 5 and len(cached_title) > 5:
                    if current_title in cached_title:
                        is_dupe = True
                        break
                    if cached_title in current_title:
                         if item.get('id'):
                            ids_to_delete.add(item['id'])
                
                # 3b. Title Similarity
                if not is_dupe and len(current_title) > 8 and len(cached_title) > 8:
                    ratio = SequenceMatcher(None, current_title, cached_title).ratio()
                    sim_threshold = 0.85
                    if same_source and time_diff < 300:
                        sim_threshold = 0.6 # Relaxed for same source & time

                    if ratio > sim_threshold:
                         if len(current_title) < len(cached_title):
                             is_dupe = True
                             break
                         else:
                             if item.get('id'):
                                ids_to_delete.add(item['id'])
        
        return is_dupe, list(ids_to_delete)

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
            "impact_score": min(score, 5), 
            "sentiment": max(min(sentiment, 1.0), -1.0), 
            "matched_rules": matched_rules,
            "tags": list(tags)
        }

    async def process(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Refresh Watchlist/Blocklist periodically (e.g., every 60s)
        now = datetime.now()
        if (now - self.last_watchlist_update).total_seconds() > 60:
            try:
                self.watchlist_keywords = await news_service.get_watchlist()
                self.last_watchlist_update = now
                # logger.debug(f"Refreshed watchlist: {len(self.watchlist_keywords)} keywords")
            except Exception as e:
                logger.warning(f"Failed to refresh watchlist: {e}")

        if (now - self.last_blocklist_update).total_seconds() > 60:
            try:
                self.blocklist_keywords = await news_service.get_blocklist()
                self.last_blocklist_update = now
            except Exception as e:
                logger.warning(f"Failed to refresh blocklist: {e}")

        raw_content = news_item.get('content', '') or news_item.get('title', '')
        if not raw_content:
            return None
            
        clean_content = self.clean_text(raw_content, source=news_item.get('source'))
        clean_title = self.clean_title(news_item.get('title', ''))
        news_item['clean_content'] = clean_content

        # Blocklist Filtering
        if self.blocklist_keywords:
            content_to_check = (clean_title + " " + clean_content).lower()
            for blocked_kw in self.blocklist_keywords:
                if blocked_kw and blocked_kw.lower() in content_to_check:
                    # logger.info(f"Blocked news item due to keyword '{blocked_kw}': {clean_title}")
                    return None

        # Yonhap Filtering Logic
        if news_item.get('source') == 'Yonhap':
            if not self.filter_yonhap_news(news_item):
                return None
        
        # Determine time for deduplication
        current_time = datetime.now()
        t_val = news_item.get('created_at') or news_item.get('time') or news_item.get('scrapedAt')
        if t_val:
            try:
                if isinstance(t_val, str):
                    # Handle common formats
                    t_val = t_val.replace(' ', 'T')
                    current_time = datetime.fromisoformat(t_val)
                elif isinstance(t_val, datetime):
                    current_time = t_val
            except: pass
            
        current_source = news_item.get('source')
        simhash = self.calculate_simhash(clean_content)
        
        if len(clean_content) > 10: # Lowered threshold slightly
            is_dupe, ids_to_delete = self.is_duplicate(simhash, clean_content, clean_title, current_time, current_source)
            
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
            'text': clean_content,
            'title': clean_title,
            'source': current_source
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
                news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 2, 5)
                break
        
        item_time = None
        if 'time' in news_item:
             try:
                 item_time = datetime.strptime(news_item['time'], '%Y-%m-%d %H:%M:%S')
             except:
                 pass
        
        expected_matches = self.match_expected_events(clean_content, item_time)
        if expected_matches:
            news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 3, 5)
            
            for event in expected_matches:
                tag = f"预期:{event['country']}{event['event']}"
                if tag not in news_item['tags']:
                    news_item['tags'].append(tag)
            
            news_item['expected_events'] = expected_matches

        # Semantic Match Storylines
        # Only perform semantic matching if content is sufficient length
        # AND exclude specific sources (like ITHome) to keep storylines finance-focused
        if clean_content and len(clean_content) > 20 and news_item.get('source') != 'ITHome':
            try:
                # Use a slightly higher threshold to ensure quality (e.g. 0.45 cosine similarity)
                matches = await vector_store.query_news_tags(clean_content, threshold=0.45)
                
                if matches:
                    matched_tags = []
                    
                    # Boost score if matched storyline
                    # Base boost for any match
                    news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 1, 5)
                    
                    for m in matches:
                        tag = f"主线:{m['title']}"
                        matched_tags.append(tag)
                        
                        # Extra boost for high confidence match
                        if m['score'] > 0.6:
                             news_item['rating']['impact_score'] = min(news_item['rating']['impact_score'] + 1, 5)

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
