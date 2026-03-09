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
current_tasks: Dict[str, Dict[str, Any]] = {}
failed_tasks_count = 0
processed_count = 0
last_processed_time = datetime.now()

# Concurrency control
fast_sem: Optional[asyncio.Semaphore] = None
standard_sem: Optional[asyncio.Semaphore] = None

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
    if settings.FAST_LLM_CONFIGS:
        fast_max_concurrency = sum(config.get("concurrency", 4) for config in settings.FAST_LLM_CONFIGS)
    else:
        fast_max_concurrency = 4

    if settings.LLM_CONFIGS:
        standard_max_concurrency = sum(config.get("concurrency", 8) for config in settings.LLM_CONFIGS)
    else:
        standard_max_concurrency = 8
    
    return {
        "isRunning": is_running,
        "currentTasks": list(current_tasks.values()),
        "schedulerRunning": scheduler.running,
        "failedCount": failed_tasks_count,
        "processedCount": processed_count,
        "lastProcessedTime": last_processed_time.isoformat() if last_processed_time else None,
        "maxConcurrency": fast_max_concurrency,
        "fastMaxConcurrency": fast_max_concurrency,
        "standardMaxConcurrency": standard_max_concurrency
    }

async def get_semaphore(mode: str = "fast"):
    global fast_sem, standard_sem

    if mode == "fast":
        if fast_sem is None:
            if settings.FAST_LLM_CONFIGS:
                total_concurrency = sum(config.get("concurrency", 4) for config in settings.FAST_LLM_CONFIGS)
                client_count = len(settings.FAST_LLM_CONFIGS)
            else:
                total_concurrency = 4
                client_count = 1
            logger.info(f"Initializing Fast Semaphore with {total_concurrency} slots (Sum of {client_count} clients)")
            fast_sem = asyncio.Semaphore(total_concurrency)
        return fast_sem

    if standard_sem is None:
        if settings.LLM_CONFIGS:
            total_concurrency = sum(config.get("concurrency", 8) for config in settings.LLM_CONFIGS)
            client_count = len(settings.LLM_CONFIGS)
        else:
            total_concurrency = 8
            client_count = 1
        logger.info(f"Initializing Standard Semaphore with {total_concurrency} slots (Sum of {client_count} clients)")
        standard_sem = asyncio.Semaphore(total_concurrency)
    return standard_sem

async def process_single_news(news: Dict[str, Any], mode: str = "fast"):
    global current_tasks, failed_tasks_count, processed_count, last_processed_time
    s = await get_semaphore(mode)
    
    news_id = str(news['id'])
    
    async with s:
        try:
            current_tasks[news_id] = {
                "id": news['id'],
                "title": news.get('title') or (news.get('content')[:30] if news.get('content') else 'No Content'),
                "status": "analyzing",
                "mode": mode,
                "startTime": datetime.now().isoformat()
            }
            
            content = news.get('content') or news.get('title')
            if not content:
                logger.warning(f"News {news['id']} has no content/title. Marking as skipped.")
                # Note: news_service.save_analysis will be async later
                await news_service.save_analysis(news['id'], {'error': 'No content'})
                failed_tasks_count += 1
                return

            logger.info(f"Analyzing news {news['id']} ({mode} mode)...")
            
            # Get current watchlist
            watchlist = await news_service.get_watchlist()
            
            analysis = await analyze_news(content, watchlist=watchlist, mode=mode)
            
            # Fallback if LLM fails or returns error
            if 'error' in analysis:
                logger.warning(f"LLM failed for {news['id']}: {analysis['error']}. Using fallback.")
                analysis = fallback_sentiment_analysis(content)
                analysis['note'] = 'Fallback used due to LLM error'
                # failed_tasks_count += 1 # Optional: count fallback as failure or success? Let's count as partial success for now.
                
            # Save result
            # Note: news_service.save_analysis will be async later
            await news_service.save_analysis(news['id'], analysis)
            logger.info(f"✅ Analyzed {news['id']}: Score={analysis.get('sentiment_score', 0)}")
            processed_count += 1
            last_processed_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error processing news {news.get('id')}: {e}")
            # Note: news_service.save_analysis will be async later
            await news_service.save_analysis(news.get('id'), {'error': str(e)})
            failed_tasks_count += 1
        finally:
            if news_id in current_tasks:
                del current_tasks[news_id]

async def analysis_job():
    if not is_running:
        return

    try:
        # Check current processing count
        # If we have enough tasks running, skip this cycle to let them finish
        # But we want to fill the pool.
        # Problem: `await asyncio.gather(*tasks)` blocks until ALL tasks in this batch finish.
        # This means if 1 task takes 30s and 19 tasks take 1s, we wait 30s before fetching next batch.
        # Solution: Don't await gather. Fire and forget (with semaphore control).
        
        processing_mode = "fast"
        await get_semaphore(processing_mode)

        if settings.FAST_LLM_CONFIGS:
            max_concurrency = sum(config.get("concurrency", 4) for config in settings.FAST_LLM_CONFIGS)
        else:
            max_concurrency = 4

        current_count = sum(1 for task in current_tasks.values() if task.get("mode") == processing_mode)
        free_slots = max_concurrency - current_count
        
        if free_slots <= 0:
            logger.info(f"Task pool full ({current_count}/{max_concurrency}) for {processing_mode}. Waiting...")
            return

        # Fetch only what we can process
        # limit = free_slots + buffer? Let's just fetch free_slots
        # Note: news_service.get_unanalyzed_news will be async later
        news_list = await news_service.get_unanalyzed_news(limit=free_slots)
        
        if not news_list:
            return

        logger.info(f"Found {len(news_list)} unanalyzed news items. Starting background tasks... (Mode: {processing_mode}, Pool: {current_count}/{max_concurrency})")
        
        # Create background tasks for each news item
        for news in news_list:
            # We must create task to run in background
            asyncio.create_task(process_single_news(news, mode=processing_mode))
            # Slight delay to avoid burst rate limits (429)
            await asyncio.sleep(0.5)
            
    except Exception as e:
        logger.error(f"Analysis job error: {e}")

async def start_scheduler():
    await load_sentiment_dicts()
    
    # Add job: run every 5 seconds (High Frequency) to avoid backlog
    scheduler.add_job(
        analysis_job, 
        IntervalTrigger(seconds=5), 
        id='analysis_job', 
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    
    scheduler.start()
    logger.info("Analysis Scheduler started with 5 second interval.")
    
    # Schedule an immediate run
    # asyncio.create_task(analysis_job())
