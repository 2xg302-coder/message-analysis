import httpx
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any
import re
from core.logging import get_logger

logger = get_logger("yonhap_collector")

class YonhapCollector:
    def __init__(self):
        self.source = 'Yonhap'
        self.rss_sources = [
            {'url': 'https://cn.yna.co.kr/RSS/politics.xml', 'category': 'politics'},
            {'url': 'https://cn.yna.co.kr/RSS/news.xml', 'category': 'general'},
            {'url': 'https://cn.yna.co.kr/RSS/economy.xml', 'category': 'economy'},
            {'url': 'https://cn.yna.co.kr/RSS/society.xml', 'category': 'society'},
        ]

    def clean_html(self, raw_html: str) -> str:
        """Remove HTML tags from string"""
        if not raw_html:
            return ""
        # Remove script and style elements
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext.strip()

    def generate_id(self, link: str) -> str:
        """Generate a unique ID based on link"""
        return hashlib.md5(link.encode('utf-8')).hexdigest()

    def collect(self) -> List[Dict[str, Any]]:
        news_list = []
        
        for source_info in self.rss_sources:
            url = source_info['url']
            category = source_info['category']
            
            try:
                # Use httpx to fetch RSS
                # Yonhap might block requests without user agent
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = httpx.get(url, headers=headers, timeout=15.0)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {url}, status code: {response.status_code}")
                    continue

                # Parse XML
                try:
                    content_str = response.content.decode('utf-8', errors='ignore')
                    root = ET.fromstring(content_str)
                except ET.ParseError as e:
                    logger.error(f"XML Parse Error for {url}: {e}")
                    continue
                
                # Iterate through items
                for item in root.findall('.//item'):
                    title = item.find('title').text if item.find('title') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else ''
                    description = item.find('description').text if item.find('description') is not None else ''
                    pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                    
                    if not title or not link:
                        continue

                    # Format time
                    # Yonhap RSS date format: Mon, 11 Mar 2024 14:30:00 +0900 (RFC 822)
                    full_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if pubDate:
                        try:
                            dt = parsedate_to_datetime(pubDate)
                            # Convert to naive datetime (or keep timezone if your system supports it, but existing code uses naive mostly)
                            # Assuming server runs in local time or UTC. 
                            # Let's format it to standard string.
                            full_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception as e:
                            logger.debug(f"Date parse error: {e}")
                            pass

                    content = self.clean_html(description)
                    if not content:
                        content = title

                    news_item = {
                        'id': self.generate_id(link),
                        'title': title,
                        'content': content,
                        'link': link,
                        'time': full_time,
                        'source': 'Yonhap', # Match source name
                        'type': 'article',
                        'scrapedAt': datetime.now().isoformat(),
                        'raw_tags': category # Pass category for processor filtering
                    }
                    news_list.append(news_item)
                    
            except Exception as e:
                logger.error(f"Error fetching Yonhap RSS {url}: {e}")
            
        return news_list
