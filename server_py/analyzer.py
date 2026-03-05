import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import get_unanalyzed_news, save_analysis, get_series_list
from llm_service import analyze_news
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
scheduler = AsyncIOScheduler()
is_running = True
current_task: Optional[Dict[str, Any]] = None

# Sentiment dictionaries
positive_words = set()
negative_words = set()

def load_sentiment_dicts():
    global positive_words, negative_words
    try:
        if os.path.exists(settings.POSITIVE_WORDS_PATH):
            with open(settings.POSITIVE_WORDS_PATH, 'r', encoding='utf-8') as f:
                positive_words = set(line.strip() for line in f if line.strip())
        
        if os.path.exists(settings.NEGATIVE_WORDS_PATH):
            with open(settings.NEGATIVE_WORDS_PATH, 'r', encoding='utf-8') as f:
                negative_words = set(line.strip() for line in f if line.strip())
                
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

async def process_single_news(news: Dict[str, Any]):
    global current_task
    
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
            save_analysis(news['id'], {'error': 'No content'})
            return

        logger.info(f"Analyzing news {news['id']}...")
        
        # LLM Analysis
        analysis = await analyze_news(content)
        
        # Fallback if LLM fails or returns error
        if 'error' in analysis:
            logger.warning(f"LLM failed for {news['id']}: {analysis['error']}. Using fallback.")
            analysis = fallback_sentiment_analysis(content)
            analysis['note'] = 'Fallback used due to LLM error'
            
        # Save result
        save_analysis(news['id'], analysis)
        logger.info(f"✅ Analyzed {news['id']}: Score={analysis.get('sentiment_score', 0)}")
        
    except Exception as e:
        logger.error(f"Error processing news {news.get('id')}: {e}")
        save_analysis(news.get('id'), {'error': str(e)})
    finally:
        current_task = None

async def analysis_job():
    if not is_running:
        return

    logger.info("⏰ Scheduled analysis job started...")
    
    try:
        # Get batch of unanalyzed news
        # Requirement says "Batch send to LLM".
        # We process a batch of 5 items per job run
        news_list = get_unanalyzed_news(limit=5)
        
        if not news_list:
            logger.info("No unanalyzed news found.")
            return

        logger.info(f"Found {len(news_list)} unanalyzed news items.")
        
        for news in news_list:
            if not is_running:
                break
            await process_single_news(news)
            # Rate limiting sleep between items
            await asyncio.sleep(1) 
            
    except Exception as e:
        logger.error(f"Analysis job error: {e}")

def start_scheduler():
    load_sentiment_dicts()
    
    # Add job: run every 5 minutes
    scheduler.add_job(analysis_job, IntervalTrigger(minutes=5), id='analysis_job', replace_existing=True)
    
    scheduler.start()
    logger.info("Analysis Scheduler started with 5 minute interval.")
    
    # Schedule an immediate run
    # asyncio.create_task(analysis_job())
