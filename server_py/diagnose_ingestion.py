import sys
import asyncio
from datetime import datetime
import json

# Add current dir to path to import modules
sys.path.append(".")

# Mock settings if needed
import os
os.environ["DEEPSEEK_API_KEY"] = "mock_key"

print("🔍 Starting Diagnosis...")

# 1. Check Imports
print("\n[1/5] Checking Dependencies...")
try:
    import akshare
    print(f"✅ akshare: {akshare.__version__}")
except ImportError as e:
    print(f"❌ akshare missing: {e}")

try:
    import simhash
    print("✅ simhash: Installed")
except ImportError as e:
    print(f"❌ simhash missing: {e}")

try:
    from flashtext import KeywordProcessor
    print("✅ flashtext: Installed")
except ImportError as e:
    print(f"❌ flashtext missing: {e}")

# 2. Check Database
print("\n[2/5] Checking Database...")
try:
    from database import init_db, get_db_connection, add_news_batch, get_stats
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM news")
    count = cursor.fetchone()['count']
    print(f"✅ Database connected. Current news count: {count}")
    conn.close()
except Exception as e:
    print(f"❌ Database error: {e}")

# 3. Test Collector (Sina)
print("\n[3/5] Testing Sina Collector (Network Request)...")
try:
    from collectors.sina_collector import SinaCollector
    collector = SinaCollector()
    print("   Requesting data from akshare (this may take 10-20s)...")
    news_list = collector.collect()
    print(f"✅ Collector returned {len(news_list)} items.")
    if len(news_list) > 0:
        print(f"   Sample title: {news_list[0].get('title')}")
except Exception as e:
    print(f"❌ Collector error: {e}")
    news_list = []

# 4. Test Processor
print("\n[4/5] Testing Processor...")
processed_list = []
if news_list:
    try:
        from processor import NewsProcessor
        processor = NewsProcessor()
        print("   Processing items...")
        for item in news_list[:5]: # Test first 5
            processed = processor.process(item)
            if processed:
                # Mimic main.py logic
                if 'rating' in processed:
                    processed['impact_score'] = processed['rating'].get('impact_score', 0)
                    processed['sentiment_score'] = processed['rating'].get('sentiment', 0.0)
                
                if 'entities' in processed and isinstance(processed['entities'], list):
                    ent_dict = {}
                    for ent in processed['entities']:
                        if isinstance(ent, dict):
                            ent_dict[ent.get('name', 'Unknown')] = ent.get('code', 'Stock')
                        elif isinstance(ent, str):
                            ent_dict[ent] = 'Keyword'
                    processed['entities'] = ent_dict
                
                processed_list.append(processed)
        print(f"✅ Processed {len(processed_list)} items successfully.")
    except Exception as e:
        print(f"❌ Processor error: {e}")
else:
    print("⚠️ Skipping processor test (no news collected).")

# 5. Test Database Write
print("\n[5/5] Testing Database Write...")
if processed_list:
    try:
        count = add_news_batch(processed_list)
        print(f"✅ Successfully wrote {count} items to database.")
        
        # Verify
        stats = get_stats()
        print(f"   Final DB Stats: Total={stats['total']}, Analyzed={stats['analyzed']}")
    except Exception as e:
        print(f"❌ Database write error: {e}")
else:
    print("⚠️ Skipping write test (no processed items).")

print("\n🏁 Diagnosis Complete.")
