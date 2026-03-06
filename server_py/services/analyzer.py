import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.news_service import news_service
from llm_service import analyze_news
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
scheduler = AsyncIOScheduler()
is_running = True
current_task: Optional[Dict[str, Any]] = None

# Concurrency control
sem: Optional[asyncio.Semaphore] = None

# Sentiment dictionaries
positive_words = set()
negative_words = set()

async def load_sentiment_dicts():
    global positive_words, negative_words
    try:
        def _read_file(path):
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return set(line.strip() for line in f if line.strip())
            return set()

        if settings.POSITIVE_WORDS_PATH:
            positive_words = await asyncio.to_thread(_read_file, settings.POSITIVE_WORDS_PATH)
        
        if settings.NEGATIVE_WORDS_PATH:
            negative_words = await asyncio.to_thread(_read_file, settings.NEGATIVE_WORDS_PATH)
                
        logger.info(f"Loaded sentiment dicts: {len(positive_words)} positive, {len(negative_words)} negative")
    except Exception as e:
        logger.error(f"Error loading sentiment dicts: {e}")

def fallback_sentiment_analysis(text: str) -> Dict[str, Any]:
    if not text:
        return {"sentiment_score": 0.0, "reasoning": "No content", "impact_score": 0}
        
    score = 0.0
    found_pos = []
    found_neg = []
    
    for word in positive_words:
        if word in text:
            score += 0.2
            found_pos.append(word)
            
    for word in negative_words:
        if word in text:
            score -= 0.2
            found_neg.append(word)
            
    # Normalize to -1.0 to 1.0 range
    final_score = max(min(score, 1.0), -1.0)
    
    # Estimate impact based on keyword density
    impact_score = min(5, int(len(found_pos) + len(found_neg) / 2) + 1)
    
    return {
        "summary": text[:100] + "..." if len(text) > 100 else text,
        "entities": {},
        "tags": ["Auto-Analyzed"],
        "impact_score": impact_score, 
        "sentiment_score": round(final_score, 2),
        "event_type": "其他",
        "reasoning": f"Fallback analysis. Found positive: {found_pos}, negative: {found_neg}"
    }

def set_analysis_status(status: bool):
    global is_running
    is_running = status
    if is_running:
        if scheduler.state == 0: # STATE_STOPPED
            scheduler.start()
        elif scheduler.state == 2: # STATE_PAUSED
            scheduler.resume()
        logger.info("Analysis Scheduler RESUMED")
    else:
        if scheduler.running:
            scheduler.pause()
        logger.info("Analysis Scheduler PAUSED")

def get_analysis_status():
    return {
        "isRunning": is_running,
        "currentTask": current_task,
        "schedulerRunning": scheduler.running
    }

async def get_semaphore():
    global sem
    if sem is None:
        sem = asyncio.Semaphore(5) # Limit to 5 concurrent LLM calls
    return sem

async def process_single_news(news: Dict[str, Any]):
    global current_task
    s = await get_semaphore()
    
    async with s:
        try:
            current_task = {
                "id": news['id'],
                "title": news.get('title') or (news.get('content')[:30] if news.get('content') else 'No Content'),
                "status": "analyzing",
                "startTime": datetime.now().isoformat()
            }
            
            content = news.get('content') or news.get('title')
            if not content:
                logger.warning(f"News {news['id']} has no content/title. Marking as skipped.")
                # Note: news_service.save_analysis will be async later
                await news_service.save_analysis(news['id'], {'error': 'No content'})
                return

            logger.info(f"Analyzing news {news['id']} (Fast Mode)...")
            
            # Get current watchlist
            watchlist = await news_service.get_watchlist()
            
            # LLM Analysis (Fast Mode)
            # Since FAST_LLM_* is disabled in .env, this will fallback to Main Client using the new configuration
            # The 'mode="fast"' parameter will still be passed, but llm_service will route it correctly
            analysis = await analyze_news(content, watchlist=watchlist, mode="standard")
            
            # Fallback if LLM fails or returns error
            if 'error' in analysis:
                logger.warning(f"LLM failed for {news['id']}: {analysis['error']}. Using fallback.")
                analysis = fallback_sentiment_analysis(content)
                analysis['note'] = 'Fallback used due to LLM error'
                
            # Save result
            # Note: news_service.save_analysis will be async later
            await news_service.save_analysis(news['id'], analysis)
            logger.info(f"✅ Analyzed {news['id']}: Score={analysis.get('sentiment_score', 0)}")
            
        except Exception as e:
            logger.error(f"Error processing news {news.get('id')}: {e}")
            # Note: news_service.save_analysis will be async later
            await news_service.save_analysis(news.get('id'), {'error': str(e)})
        finally:
            current_task = None

async def analysis_job():
    if not is_running:
        return

    try:
        # Get batch of unanalyzed news
        # Note: news_service.get_unanalyzed_news will be async later
        news_list = await news_service.get_unanalyzed_news(limit=5)
        
        if not news_list:
            return

        logger.info(f"Found {len(news_list)} unanalyzed news items. Processing batch...")
        
        # Concurrent processing with semaphore
        tasks = [process_single_news(news) for news in news_list]
        await asyncio.gather(*tasks)
            
    except Exception as e:
        logger.error(f"Analysis job error: {e}")

async def start_scheduler():
    await load_sentiment_dicts()
    
    # Add job: run every 30 seconds (Normal Frequency) to avoid overlap warnings
    scheduler.add_job(
        analysis_job, 
        IntervalTrigger(seconds=30), 
        id='analysis_job', 
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    
    scheduler.start()
    logger.info("Analysis Scheduler started with 30 second interval.")
    
    # Schedule an immediate run
    # asyncio.create_task(analysis_job())