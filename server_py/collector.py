import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from collectors.sina_collector import SinaCollector
from collectors.eastmoney_collector import EastMoneyCollector
from processor import NewsProcessor
from database import add_news_batch

class CollectorService:
    def __init__(self):
        print("🔧 Initializing Collector Service...")
        self.sina = SinaCollector()
        self.eastmoney = EastMoneyCollector()
        self.processor = NewsProcessor()
        
    def run_sina(self):
        raw_news = self.sina.collect()
        self.process_and_save(raw_news)
        
    def run_eastmoney(self):
        raw_news = self.eastmoney.collect()
        self.process_and_save(raw_news)
        
    def process_and_save(self, news_list):
        if not news_list:
            return
            
        processed_list = []
        for item in news_list:
            processed = self.processor.process(item)
            if processed:
                processed_list.append(processed)
                
        if processed_list:
            count = add_news_batch(processed_list)
            print(f"💾 Saved {count} new items to database.")
        else:
            print("DATA: No new valid items to save (all duplicates or filtered).")

    def start(self):
        print("🚀 Starting Collector Service with Scheduler...")
        scheduler = BlockingScheduler()
        
        # Add jobs
        # Sina: 30s
        scheduler.add_job(self.run_sina, 'interval', seconds=30)
        
        # EastMoney: 5m
        scheduler.add_job(self.run_eastmoney, 'interval', minutes=5)
        
        # Run immediately once before scheduler starts
        print("⚡ Running initial collection...")
        self.run_sina()
        self.run_eastmoney()
        
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("🛑 Collector Service stopped.")

if __name__ == "__main__":
    service = CollectorService()
    service.start()
