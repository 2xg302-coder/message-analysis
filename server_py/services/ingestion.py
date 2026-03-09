import asyncio
from datetime import datetime
from typing import Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core.logging import get_logger
from services.news_service import news_service
from core.database import db

logger = get_logger("ingestion_service")

# Global scheduler for ingestion
scheduler = AsyncIOScheduler()
SOURCE_JOB_CONFIGS = {
    "Sina": {"job_id": "sina_ingestion", "trigger": lambda: IntervalTrigger(seconds=30)},
    "EastMoney": {"job_id": "em_ingestion", "trigger": lambda: IntervalTrigger(minutes=5)},
    "ITHome": {"job_id": "ithome_ingestion", "trigger": lambda: IntervalTrigger(minutes=10)},
    "CCTV": {"job_id": "cctv_ingestion", "trigger": lambda: IntervalTrigger(minutes=60)},
    "PeopleDaily": {"job_id": "peopledaily_ingestion", "trigger": lambda: IntervalTrigger(minutes=30)},
}
source_collectors: Dict[str, object] = {}
news_processor = None
calendar_collector_instance = None

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
    today_str = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"Checking calendar data for {today_str}...")
    
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

async def _ensure_source_config_defaults():
    current_time = datetime.now().isoformat()
    params = [(source, 1, current_time) for source in SOURCE_JOB_CONFIGS.keys()]
    await db.execute_many(
        "INSERT OR IGNORE INTO ingestion_source_config (source, enabled, updated_at) VALUES (?, ?, ?)",
        params
    )

async def get_source_configs():
    await _ensure_source_config_defaults()
    rows = await db.execute_query(
        "SELECT source, enabled FROM ingestion_source_config ORDER BY source ASC"
    )
    return [{"source": row["source"], "enabled": bool(row["enabled"])} for row in rows]

async def _load_source_enabled_map():
    configs = await get_source_configs()
    return {item["source"]: item["enabled"] for item in configs}

def _add_source_job(source_name: str):
    if source_name not in SOURCE_JOB_CONFIGS:
        return
    collector = source_collectors.get(source_name)
    if not collector or not news_processor:
        return
    cfg = SOURCE_JOB_CONFIGS[source_name]
    scheduler.add_job(
        run_ingestion,
        cfg["trigger"](),
        args=[collector, source_name, news_processor],
        id=cfg["job_id"],
        replace_existing=True
    )

async def set_source_enabled(source: str, enabled: bool):
    if source not in SOURCE_JOB_CONFIGS:
        raise ValueError(f"Unsupported source: {source}")
    current_time = datetime.now().isoformat()
    ok = await db.execute_update(
        """
        INSERT INTO ingestion_source_config (source, enabled, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            enabled=excluded.enabled,
            updated_at=excluded.updated_at
        """,
        (source, 1 if enabled else 0, current_time)
    )
    if not ok:
        raise RuntimeError("Failed to update source config")
    await refresh_source_jobs()

async def refresh_source_jobs():
    if not scheduler.running:
        return
    enabled_map = await _load_source_enabled_map()
    for source_name, cfg in SOURCE_JOB_CONFIGS.items():
        should_enable = enabled_map.get(source_name, True)
        job = scheduler.get_job(cfg["job_id"])
        if should_enable and job is None:
            _add_source_job(source_name)
            logger.info(f"Enabled ingestion job for source: {source_name}")
        if not should_enable and job is not None:
            scheduler.remove_job(cfg["job_id"])
            logger.info(f"Disabled ingestion job for source: {source_name}")

async def start_ingestion_scheduler():
    global news_processor, calendar_collector_instance
    try:
        # Import here to avoid circular imports or early initialization issues
        from collectors.sina_collector import SinaCollector
        from collectors.eastmoney_collector import EastMoneyCollector
        from collectors.calendar_collector import CalendarCollector
        from collectors.ithome_collector import ITHomeCollector
        from collectors.cctv_collector import CCTVCollector
        from collectors.people_daily_collector import PeopleDailyCollector
        from services.processor import NewsProcessor
        
        source_collectors["Sina"] = SinaCollector()
        source_collectors["EastMoney"] = EastMoneyCollector()
        source_collectors["ITHome"] = ITHomeCollector()
        source_collectors["CCTV"] = CCTVCollector()
        source_collectors["PeopleDaily"] = PeopleDailyCollector()
        calendar_collector_instance = CalendarCollector(data_dir="data")
        news_processor = NewsProcessor()
        # Initialize processor async state (cache)
        # Since we are in an async function, we can await it directly or create task
        await news_processor.init_async()
        enabled_map = await _load_source_enabled_map()
        for source_name in SOURCE_JOB_CONFIGS.keys():
            if enabled_map.get(source_name, True):
                _add_source_job(source_name)
        
        # Calendar Collection Job (Daily at 08:00)
        scheduler.add_job(
            run_calendar_collection,
            CronTrigger(hour=8, minute=0),
            args=[calendar_collector_instance, news_processor],
            id='calendar_collection',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Ingestion Scheduler started.")
        
        # Run immediately but with a small delay to allow server startup
        async def delayed_start():
            await asyncio.sleep(5)  # Wait 5 seconds
            logger.info("Starting initial ingestion tasks...")
            current_enabled_map = await _load_source_enabled_map()
            if current_enabled_map.get("Sina", True):
                await run_ingestion(source_collectors["Sina"], "Sina", news_processor)
            if current_enabled_map.get("ITHome", True):
                await run_ingestion(source_collectors["ITHome"], "ITHome", news_processor)
            
            # 2. Daily/Low frequency sources - Check if needed
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # Check CCTV
            if current_enabled_map.get("CCTV", True):
                try:
                    cctv_query = "SELECT COUNT(*) as count FROM news WHERE source = 'CCTV' AND time LIKE ?"
                    cctv_res = await db.execute_query(cctv_query, (f'{today_str}%',))
                    cctv_count = cctv_res[0]['count'] if cctv_res else 0
                    
                    if cctv_count > 0:
                        logger.info(f"CCTV news for {today_str} already exists ({cctv_count} items). Skipping startup collection.")
                    else:
                        await run_ingestion(source_collectors["CCTV"], "CCTV", news_processor)
                except Exception as e:
                    logger.error(f"Error checking CCTV status: {e}")
                    await run_ingestion(source_collectors["CCTV"], "CCTV", news_processor)

            if current_enabled_map.get("PeopleDaily", True):
                await run_ingestion(source_collectors["PeopleDaily"], "PeopleDaily", news_processor)
            
            # Calendar - Already has check inside run_calendar_collection
            await run_calendar_collection(calendar_collector_instance, news_processor)

        asyncio.create_task(delayed_start())
        
    except ImportError as e:
        logger.warning(f"Collectors or Processor not available: {e}")
    except Exception as e:
        logger.error(f"Ingestion Scheduler startup error: {e}")

def stop_ingestion_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Ingestion Scheduler stopped.")
