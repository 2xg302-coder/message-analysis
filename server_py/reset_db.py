import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'news.db')
print(f"Connecting to database at {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Resetting analysis fields...")
    cursor.execute("UPDATE news SET analysis = NULL, analyzed_at = NULL, impact_score = 0, sentiment_score = 0.0, tags = '[]', entities = '{}'")
    conn.commit()
    
    rows_affected = cursor.rowcount
    print(f"Database reset successfully: {rows_affected} rows updated.")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
