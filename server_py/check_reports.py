import httpx
import asyncio
from datetime import datetime, timedelta

async def check_api():
    url = "http://localhost:8000/api/reports/daily"
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    async with httpx.AsyncClient() as client:
        # Check yesterday (default)
        print(f"Checking yesterday ({yesterday})...")
        try:
            resp = await client.get(url, params={"date": yesterday})
            if resp.status_code == 200:
                data = resp.json()
                print("Yesterday's Data:", data)
            else:
                print(f"Failed yesterday: {resp.status_code}")
        except Exception as e:
            print(f"Error checking yesterday: {e}")

        # Check today
        print(f"Checking today ({today})...")
        try:
            resp = await client.get(url, params={"date": today})
            if resp.status_code == 200:
                data = resp.json()
                print("Today's Data:", data)
            else:
                print(f"Failed today: {resp.status_code}")
        except Exception as e:
            print(f"Error checking today: {e}")

if __name__ == "__main__":
    asyncio.run(check_api())
