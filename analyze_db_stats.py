import sqlite3
import os
from datetime import datetime

# 配置数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'server_py/news.db')

def analyze_news_stats():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. 总数据量
        cursor.execute("SELECT COUNT(*) FROM news")
        total_count = cursor.fetchone()[0]
        print(f"\nTotal News Count: {total_count}")

        if total_count == 0:
            print("Database is empty.")
            return

        # 2. Impact Score 分布
        print("\nImpact Score Distribution:")
        
        # High Value (>= 7)
        cursor.execute("SELECT COUNT(*) FROM news WHERE impact_score >= 7")
        high_val_count = cursor.fetchone()[0]
        print(f"  High Value (>= 7): {high_val_count} ({high_val_count/total_count*100:.1f}%)")

        # Medium Value (4-6)
        cursor.execute("SELECT COUNT(*) FROM news WHERE impact_score >= 4 AND impact_score <= 6")
        mid_val_count = cursor.fetchone()[0]
        print(f"  Medium Value (4-6): {mid_val_count} ({mid_val_count/total_count*100:.1f}%)")

        # Low Value (< 4, excluding 0/NULL if they mean unanalyzed)
        # Assuming 0 or NULL means unanalyzed or very low. Let's check 1-3.
        cursor.execute("SELECT COUNT(*) FROM news WHERE impact_score >= 1 AND impact_score <= 3")
        low_val_count = cursor.fetchone()[0]
        print(f"  Low Value (1-3):   {low_val_count} ({low_val_count/total_count*100:.1f}%)")

        # Unanalyzed or Zero (<= 0 or NULL)
        cursor.execute("SELECT COUNT(*) FROM news WHERE impact_score IS NULL OR impact_score <= 0")
        unanalyzed_count = cursor.fetchone()[0]
        print(f"  Unanalyzed/Zero:   {unanalyzed_count} ({unanalyzed_count/total_count*100:.1f}%)")

        # 3. 时间范围
        print("\nTime Range:")
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM news")
        min_time, max_time = cursor.fetchone()
        print(f"  Earliest: {min_time}")
        print(f"  Latest:   {max_time}")

        # 4. 每日数据量趋势 (最近 7 天)
        print("\nRecent Daily Volume (Last 7 Days with data):")
        cursor.execute("""
            SELECT date(created_at) as date, COUNT(*) 
            FROM news 
            GROUP BY date(created_at) 
            ORDER BY date DESC 
            LIMIT 7
        """)
        daily_stats = cursor.fetchall()
        for date, count in daily_stats:
            print(f"  {date}: {count}")

        # 5. 分析是否有 Storyline 引用 (Proxy for 'Very High Value')
        # Check if storyline table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='storylines'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM storylines")
            storyline_count = cursor.fetchone()[0]
            print(f"\nTotal Storylines: {storyline_count}")
        else:
            print("\nStorylines table not found.")

    except Exception as e:
        print(f"Error analyzing database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_news_stats()
