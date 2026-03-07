
import sqlite3
import json
import sys

# Add server_py to path
sys.path.append("/home/aaa/projects/message-analysis/server_py")

from config import settings

def retry_failed_analysis():
    db_path = settings.DB_PATH
    print(f"Database path: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find count of failed analysis
        cursor.execute("SELECT COUNT(*) FROM news WHERE analysis LIKE '%Fallback used due to LLM error%'")
        count = cursor.fetchone()[0]
        
        print(f"Found {count} items with failed analysis.")
        
        if count > 0:
            # Reset analysis to NULL
            print("Resetting analysis for these items...")
            cursor.execute("UPDATE news SET analysis = NULL, analyzed_at = NULL WHERE analysis LIKE '%Fallback used due to LLM error%'")
            conn.commit()
            print(f"Successfully reset {cursor.rowcount} items. The analyzer service will pick them up shortly.")
        else:
            print("No items to reset.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    retry_failed_analysis()
