import sqlite3
import json

db_path = 'server_py/news.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Checking tags format in database:")
cursor.execute("SELECT id, tags FROM news WHERE tags IS NOT NULL LIMIT 5")
for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"Tags (Raw): {row[1]}")
    try:
        tags_list = json.loads(row[1])
        print(f"Tags (Parsed): {tags_list}")
    except:
        print("Tags parse failed")
    print("-" * 20)

print("\nTesting search for '南向资金':")
# Test raw search
cursor.execute("SELECT count(*) FROM news WHERE tags LIKE '%南向资金%'")
print(f"Raw query count: {cursor.fetchone()[0]}")

# Test unicode escape search
tag = "南向资金"
json_tag = json.dumps([tag]).strip('[]"') # get \uXXXX representation if any
print(f"JSON dump of tag: {json.dumps([tag])}")

conn.close()
