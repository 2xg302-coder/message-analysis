import asyncio
import json
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.news_service import news_service
from llm_service import call_llm
from core.database import db

async def merge_tags():
    print("Fetching all event tags...")
    
    # 1. Fetch all news with event_tags
    query = "SELECT id, analysis FROM news WHERE analysis IS NOT NULL AND analysis LIKE '%\"event_tag\"%'"
    rows = await db.execute_query(query)
    
    tag_counts = {}
    news_map = {} # tag -> [news_id1, news_id2, ...]

    for row in rows:
        try:
            analysis = json.loads(row['analysis'])
            tag = analysis.get('event_tag')
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if tag not in news_map:
                    news_map[tag] = []
                news_map[tag].append(row['id'])
        except:
            continue
            
    unique_tags = list(tag_counts.keys())
    print(f"Found {len(unique_tags)} unique tags.")
    if len(unique_tags) == 0:
        print("No tags found.")
        return

    # 2. Ask LLM to group them
    print("Asking LLM to group similar tags...")
    
    prompt = f"""
    以下是数据库中现有的“事件标签”列表。由于生成不规范，存在很多含义相同但写法不同的标签（例如“美伊关系”、“美伊局势”、“中东紧张局势”可能都指同一个大事）。
    
    请你将这些标签归类合并。
    要求：
    1. 识别出语义重复或高度相关的标签。
    2. 为每一组选择一个最简短、最通用的“标准名称”（2-4个字最好，如“中东局势”、“俄乌冲突”）。
    3. 输出 JSON 格式：{{ "标准名称1": ["同义词1", "同义词2", ...], "标准名称2": [...] }}
    4. 如果某个标签本身就很标准且没有同义词，不需要包含在返回结果中（保持原样）。
    
    标签列表：
    {json.dumps(unique_tags, ensure_ascii=False)}
    """
    
    messages = [
        {"role": "system", "content": "你是一个数据清洗专家，负责标准化事件标签。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        mapping = await call_llm(messages, timeout=60)
    except Exception as e:
        print(f"LLM call failed: {e}")
        return

    print("LLM suggestions:")
    print(json.dumps(mapping, ensure_ascii=False, indent=2))
    
    # 3. Apply updates
    updates_count = 0
    
    for canonical, synonyms in mapping.items():
        # Ensure canonical is not in synonyms to avoid redundant updates, 
        # but we might need to update 'canonical' itself if we want to standardize it? 
        # The prompt implies synonyms map TO canonical.
        
        # We want to update all news items that have any tag in `synonyms` to have `canonical`.
        # Also if the tag IS `canonical`, no need to update unless we are fixing format.
        
        target_ids = set()
        for syn in synonyms:
            if syn in news_map:
                target_ids.update(news_map[syn])
        
        # Also check if canonical itself exists in the original map but we want to make sure everyone uses it
        # Actually, the logic is: for every news item that has a tag in `synonyms`, set tag to `canonical`.
        
        if not target_ids:
            continue
            
        print(f"Merging {len(target_ids)} items into '{canonical}' (from {synonyms})")
        
        for news_id in target_ids:
            # We need to fetch the row again to be safe, or just update blindly?
            # Better to fetch-modify-save to preserve other analysis fields.
            
            # Since we have raw SQL access, we can do a smart update if SQLite supports JSON.
            # But python-side update is safer for logic.
            
            # Fetch current analysis
            row = await db.execute_query("SELECT analysis FROM news WHERE id = ?", (news_id,))
            if not row:
                continue
                
            try:
                current_analysis = json.loads(row[0]['analysis'])
                old_tag = current_analysis.get('event_tag')
                
                if old_tag == canonical:
                    continue
                    
                current_analysis['event_tag'] = canonical
                
                # Update DB
                await db.execute_update(
                    "UPDATE news SET analysis = ? WHERE id = ?", 
                    (json.dumps(current_analysis, ensure_ascii=False), news_id)
                )
                updates_count += 1
            except Exception as e:
                print(f"Error updating news {news_id}: {e}")

    print(f"Done! Updated {updates_count} records.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(merge_tags())
