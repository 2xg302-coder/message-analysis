import httpx
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any
import re

class PeopleDailyCollector:
    def __init__(self):
        self.source = 'PeopleDaily'
        self.rss_urls = [
            'http://www.people.com.cn/rss/politics.xml', # 时政
            'http://www.people.com.cn/rss/world.xml',    # 国际
            'http://www.people.com.cn/rss/finance.xml',  # 金融
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
        
        for url in self.rss_urls:
            try:
                # Use httpx to fetch RSS
                response = httpx.get(url, timeout=10.0)
                # response.raise_for_status() # Some RSS feeds might fail, just skip
                if response.status_code != 200:
                    continue

                # Parse XML
                try:
                    # People's Daily uses GBK or UTF-8?
                    # Try to decode with apparent_encoding or default to utf-8
                    content_str = response.content.decode('utf-8', errors='ignore')
                    # Sometimes headers say GB2312
                    if 'encoding="GB2312"' in content_str or 'encoding="gb2312"' in content_str:
                         content_str = response.content.decode('gb18030', errors='ignore')
                         
                    root = ET.fromstring(content_str)
                except ET.ParseError:
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
                    full_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if pubDate:
                        try:
                            dt = parsedate_to_datetime(pubDate)
                            full_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
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
                        'source': 'PeopleDaily',
                        'type': 'article',
                        'scrapedAt': datetime.now().isoformat(),
                        'raw_tags': ''
                    }
                    news_list.append(news_item)
                    
            except Exception as e:
                print(f"Error fetching PeopleDaily RSS {url}: {e}")
            
        return news_list
