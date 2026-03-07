import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'news.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM news WHERE analysis IS NULL")
count = cursor.fetchone()[0]

print(f"当前积压未分析新闻数量: {count}")

conn.close()
