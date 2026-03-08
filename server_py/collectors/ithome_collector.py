import httpx
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any

import re

class ITHomeCollector:
    def __init__(self):
        self.source = 'ITHome'
        self.rss_url = 'https://www.ithome.com/rss/'

    def clean_html(self, raw_html: str) -> str:
        """Remove HTML tags from string"""
        if not raw_html:
            return ""
        # Remove script and style elements
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext.strip()

    def generate_id(self, content: str, time_str: str) -> str:
        """Generate a unique ID based on content and time"""
        raw = f"{content}-{time_str}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def collect(self) -> List[Dict[str, Any]]:
        news_list = []
        try:
            # Use httpx to fetch RSS
            response = httpx.get(self.rss_url, timeout=10.0)
            response.raise_for_status()
            
            # Parse XML
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                # Sometimes encoding issues occur, try decoding first
                root = ET.fromstring(response.content.decode('utf-8', errors='ignore'))
            
            # Iterate through items
            # Standard RSS 2.0 structure: rss > channel > item
            # Using .//item finds all items recursively which is safer
            for item in root.findall('.//item'):
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                description = item.find('description').text if item.find('description') is not None else ''
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
                
                # Format time
                full_time = pubDate
                try:
                    dt = parsedate_to_datetime(pubDate)
                    # Convert to local time or keep as ISO format
                    # System seems to use string mostly. 
                    # Let's convert to YYYY-MM-DD HH:MM:SS format
                    full_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

                # ITHome content is usually in description (HTML).
                # The processor might strip HTML, but we pass it as is for now.
                content = self.clean_html(description)
                if not content:
                    content = title

                news_item = {
                    'id': self.generate_id(link, full_time), # Use link to ensure uniqueness for RSS items
                    'title': title,
                    'content': content,
                    'link': link,
                    'time': full_time,
                    'source': 'ITHome',
                    'type': 'article', # ITHome news are articles
                    'scrapedAt': datetime.now().isoformat(),
                    'raw_tags': ''
                }
                news_list.append(news_item)
                
        except Exception as e:
            print(f"Error fetching ITHome news: {e}")
            
        return news_list
