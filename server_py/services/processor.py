import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from simhash import Simhash
from flashtext import KeywordProcessor
import akshare as ak
from services.news_service import news_service
import os
import logging

logger = logging.getLogger("processor")

class NewsProcessor:
    def __init__(self):
        self.keyword_processor = KeywordProcessor()
        self.simhash_cache: List[Dict[str, Any]] = [] # {simhash, time}
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
        logger.info("Loading recent news for deduplication...")
        try:
            # Load last 1000 items (approx 24-48 hours of volume?)
            # NOTE: news_service.get_news is async now.
            # We are in __init__ (sync). We cannot call async method directly.
            # We can run it in a new event loop or just use a dedicated sync connection here since it's startup.
            # Or better, just skipping loading cache for now if it's too complex, but dedupe is important.
            # Let's use asyncio.run() if there is no loop running, but FastAPI has a loop.
            # processor is initialized in ingestion.py -> start_ingestion_scheduler -> processor = NewsProcessor()
            # start_ingestion_scheduler is called from main.py lifespan (async context manager).
            # So there is a running loop.
            
            # Since we are inside a running loop (lifespan), we cannot use asyncio.run().
            # But NewsProcessor.__init__ is synchronous.
            # We should probably make an async init method.
            pass
        except Exception as e:
            logger.error(f"Error loading recent hashes: {e}")
            
    async def init_async(self):
        logger.info("Loading recent news for deduplication (Async)...")
        try:
            recent_news = await news_service.get_news(limit=1000)
            count = 0
            for item in recent_news:
                if 'simhash' in item and item['simhash']:
                    try:
                        val = item['simhash']
                        sh = Simhash(val)
                        
                        t_str = item.get('created_at') or item.get('scrapedAt')
                        if t_str:
                            t = datetime.fromisoformat(t_str)
                            self.simhash_cache.append({'hash': sh, 'time': t})
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
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'【免责声明】.*', '', text)
        text = re.sub(r'（记者\s+.*?）', '', text)
        text = re.sub(r'\(记者\s+.*?\)', '', text)
        return text.strip()

    def calculate_simhash(self, text: str) -> Simhash:
        return Simhash(text)

    def is_duplicate(self, current_simhash: Simhash, current_time: datetime) -> bool:
        cutoff = current_time - timedelta(hours=24)
        self.simhash_cache = [x for x in self.simhash_cache if x['time'] > cutoff]
        
        for item in self.simhash_cache:
            distance = current_simhash.distance(item['hash'])
            if distance <= 3:
                return True
        return False

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

    def process(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raw_content = news_item.get('content', '') or news_item.get('title', '')
        if not raw_content:
            return None
            
        clean_content = self.clean_text(raw_content)
        news_item['clean_content'] = clean_content
        
        current_time = datetime.now()
        simhash = self.calculate_simhash(clean_content)
        
        if len(clean_content) > 20:
            if self.is_duplicate(simhash, current_time):
                return None
            
        self.simhash_cache.append({'hash': simhash, 'time': current_time})
        news_item['simhash'] = simhash.value
        
        entities = self.extract_entities(clean_content)
        news_item['entities'] = entities
        
        rating = self.rate_news(clean_content)
        news_item['rating'] = rating
        news_item['tags'] = rating.get('matched_rules', []) + rating.get('tags', [])
        
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

        return news_item