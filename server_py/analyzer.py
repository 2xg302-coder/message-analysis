import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from database import get_unanalyzed_news, save_analysis, get_series_list
from llm_service import analyze_news

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
is_running = True
current_task: Optional[Dict[str, Any]] = None

def set_analysis_status(status: bool):
    global is_running
    is_running = status
    logger.info(f"Analysis Worker status changed to: {'RUNNING' if is_running else 'PAUSED'}")

def get_analysis_status():
    return {
        "isRunning": is_running,
        "currentTask": current_task
    }

async def analysis_worker():
    global current_task, is_running
    logger.info("🚀 Analysis Worker Started...")
    
    # Wait for DB init
    await asyncio.sleep(2)
    
    while True:
        if not is_running:
            current_task = None
            await asyncio.sleep(1)
            continue
            
        try:
            # Get unanalyzed news
            news_list = get_unanalyzed_news(1)
            
            if news_list:
                news = news_list[0]
                
                # Update status
                current_task = {
                    "id": news['id'],
                    "title": news.get('title') or (news.get('content')[:30] if news.get('content') else 'No Content'),
                    "status": "analyzing",
                    "startTime": datetime.now().isoformat()
                }
                
                content = news.get('content') or news.get('title')
                if not content:
                    logger.warning(f"News {news['id']} has no content/title. Marking as skipped.")
                    save_analysis(news['id'], {'error': 'No content'})
                    continue
                
                logger.info(f"Analyzing news {news['id']}: {content[:20]}...")
                
                # Get existing tags for context
                existing_series = get_series_list()
                
                # Call LLM
                analysis = await analyze_news(content, existing_series)
                
                if 'error' in analysis:
                    logger.error(f"Skipping {news['id']} due to error: {analysis['error']}")
                    if analysis['error'] == 'No API Key':
                        logger.warning('Please configure DEEPSEEK_API_KEY in .env')
                        is_running = False
                        current_task['status'] = 'error'
                        current_task['error'] = 'Missing API Key'
                        break
                    # Save error to DB to avoid infinite loop on same item
                    save_analysis(news['id'], analysis)
                else:
                    # Save result
                    save_analysis(news['id'], analysis)
                    logger.info(f"✅ Analyzed {news['id']}: Tag={analysis.get('event_tag', 'N/A')}, Score={analysis.get('score', 0)}")
                
                # Clear task
                current_task = None
                
                # Rate limiting
                await asyncio.sleep(1)
            else:
                current_task = None
                # Wait before checking again
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")
            current_task = None
            await asyncio.sleep(2)
