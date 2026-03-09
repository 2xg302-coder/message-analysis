
import sqlite3
import json
import sys
import os

# Add server_py to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings

def retry_failed_analysis(reset_all_without_triples=False, limit=50):
    db_path = settings.DB_PATH
    print(f"Database path: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Retry failed analysis (Fallback)
        cursor.execute("SELECT COUNT(*) FROM news WHERE analysis LIKE '%Fallback used due to LLM error%'")
        failed_count = cursor.fetchone()[0]
        
        print(f"Found {failed_count} items with failed analysis (Fallback).")
        
        if failed_count > 0:
            print("Resetting analysis for failed items...")
            cursor.execute("UPDATE news SET analysis = NULL, analyzed_at = NULL WHERE analysis LIKE '%Fallback used due to LLM error%'")
            conn.commit()
            print(f"Successfully reset {cursor.rowcount} failed items.")
            
        # 2. Retry items without triples (if requested)
        if reset_all_without_triples:
            print(f"Checking for recent news without triples (limit {limit})...")
            # Logic: triples is default '[]' or NULL, but analysis exists and is valid (not fallback)
            cursor.execute("""
                SELECT id FROM news 
                WHERE (triples IS NULL OR triples = '[]') 
                AND analysis IS NOT NULL 
                AND analysis NOT LIKE '%Fallback used due to LLM error%'
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            triples_count = len(rows)
            
            print(f"Found {triples_count} items needing triples extraction.")
            
            if triples_count > 0:
                ids = [row[0] for row in rows]
                placeholders = ','.join(['?'] * len(ids))
                print("Resetting analysis for these items to trigger re-analysis...")
                cursor.execute(f"UPDATE news SET analysis = NULL, analyzed_at = NULL WHERE id IN ({placeholders})", ids)
                conn.commit()
                print(f"Successfully reset {cursor.rowcount} items for triples extraction.")
            else:
                print("No recent items found missing triples.")

        conn.close()
        print("Done. The analyzer service will pick up reset items shortly.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Check arguments
    reset_triples = "--triples" in sys.argv
    limit = 50
    for arg in sys.argv:
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=")[1])
            except:
                pass

    if reset_triples:
        print(f"Mode: Retry failed + Re-analyze for Triples (Limit {limit})")
    else:
        print("Mode: Retry failed only (Use --triples to re-analyze for triples)")
        
    retry_failed_analysis(reset_triples, limit)
