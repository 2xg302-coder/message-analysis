import asyncio
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core.logging import get_logger
from services.news_service import news_service

logger = get_logger("ingestion_service")

# Global scheduler for ingestion
scheduler = AsyncIOScheduler()

async def run_ingestion(collector, source_name, processor):
    # logger.info(f"Running ingestion for {source_name}...")
    try:
        # Run in executor to avoid blocking event loop
        news_list = await asyncio.to_thread(collector.collect)
        if news_list:
            processed_list = []
            for news in news_list:
                try:
                    # Process news (clean, dedupe, NER, rate)
                    processed = await processor.process(news)
                    if processed:
                        # Map processed fields to NewsItem/DB schema
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
                        
                        if 'tags' not in processed:
                            processed['tags'] = []
                        
                        processed_list.append(processed)
                except Exception as e:
                    logger.error(f"Error processing item from {source_name}: {e}")
            
            if processed_list:
                count = await news_service.add_news_batch(processed_list)
                logger.info(f"Saved {count} new items from {source_name}")
            else:
                pass
    except Exception as e:
        logger.error(f"Ingestion error for {source_name}: {e}")

async def run_calendar_collection(collector, processor):
    from datetime import datetime
    today_str = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"Checking calendar data for {today_str}...")
    
    # Check if we already have data for today
    from core.database import db
    try:
        count_query = "SELECT COUNT(*) as count FROM calendar_events WHERE date = ?"
        result = await db.execute_query(count_query, (today_str,))
        count = result[0]['count'] if result else 0
        
        if count > 0:
            logger.info(f"Calendar events for {today_str} already exist ({count} events). Skipping startup collection.")
            # Still load expected events into processor cache if needed
            if hasattr(processor, 'load_expected_events'):
                processor.load_expected_events()
            return
    except Exception as e:
        logger.warning(f"Failed to check existing calendar events: {e}")

    logger.info("Running daily economic calendar collection...")
    try:
        await collector.collect()
        # Reload events in processor after collection
        if hasattr(processor, 'load_expected_events'):
            processor.load_expected_events()
        logger.info("Calendar collection complete.")
    except Exception as e:
        logger.error(f"Calendar collection error: {e}")

async def start_ingestion_scheduler():
    try:
        # Import here to avoid circular imports or early initialization issues
        from collectors.sina_collector import SinaCollector
        from collectors.eastmoney_collector import EastMoneyCollector
        from collectors.calendar_collector import CalendarCollector
        from services.processor import NewsProcessor
        
        sina_collector = SinaCollector()
        em_collector = EastMoneyCollector()
        calendar_collector = CalendarCollector(data_dir="data")
        processor = NewsProcessor()
        # Initialize processor async state (cache)
        # Since we are in an async function, we can await it directly or create task
        await processor.init_async()
        
        # News Ingestion Jobs
        scheduler.add_job(run_ingestion, IntervalTrigger(seconds=30), args=[sina_collector, 'Sina', processor], id='sina_ingestion', replace_existing=True)
        scheduler.add_job(run_ingestion, IntervalTrigger(minutes=5), args=[em_collector, 'EastMoney', processor], id='em_ingestion', replace_existing=True)
        
        # Calendar Collection Job (Daily at 08:00)
        scheduler.add_job(run_calendar_collection, CronTrigger(hour=8, minute=0), args=[calendar_collector, processor], id='calendar_collection', replace_existing=True)
        
        scheduler.start()
        logger.info("Ingestion Scheduler started.")
        
        # Run immediately but with a small delay to allow server startup
        async def delayed_start():
            await asyncio.sleep(5)  # Wait 5 seconds
            logger.info("Starting initial ingestion tasks...")
            await run_ingestion(sina_collector, 'Sina', processor)
            await run_calendar_collection(calendar_collector, processor)

        asyncio.create_task(delayed_start())
        
    except ImportError as e:
        logger.warning(f"Collectors or Processor not available: {e}")
    except Exception as e:
        logger.error(f"Ingestion Scheduler startup error: {e}")

def stop_ingestion_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Ingestion Scheduler stopped.")
