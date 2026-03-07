import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.news_service import news_service
from services.analyzer import process_single_news, load_sentiment_dicts, get_semaphore
from core.logging import get_logger

logger = get_logger("manual_process")

async def manual_process():
    print("正在初始化...")
    await load_sentiment_dicts()
    
    # 获取所有未分析的新闻
    print("正在查询未处理任务...")
    # 这里我们一次性获取多一点，比如 100 条
    news_list = await news_service.get_unanalyzed_news(limit=100)
    
    total = len(news_list)
    if total == 0:
        print("没有发现未处理的任务！")
        return

    print(f"发现 {total} 条未处理任务，准备开始处理...")
    print(f"并发数: 5 (受限于 OpenRouter 速度)")

    # 复用 analyzer.py 中的处理逻辑
    # process_single_news 内部已经使用了 semaphore (默认为 5)
    # 但我们需要确保它使用正确的 semaphore
    
    tasks = []
    for i, news in enumerate(news_list):
        print(f"[{i+1}/{total}] 提交任务: {news.get('id')} - {news.get('title')[:20]}...")
        tasks.append(process_single_news(news))
    
    # 使用 asyncio.gather 并发执行
    # 注意：process_single_news 内部有 semaphore 限制并发，所以这里可以直接 gather 所有
    start_time = datetime.now()
    await asyncio.gather(*tasks)
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    print(f"\n处理完成！耗时: {duration:.2f} 秒")
    print(f"平均速度: {duration/total:.2f} 秒/条")

if __name__ == "__main__":
    try:
        asyncio.run(manual_process())
    except KeyboardInterrupt:
        print("\n用户手动停止")
    except Exception as e:
        print(f"\n发生错误: {e}")
