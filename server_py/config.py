import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../server/news.db"))

settings = Settings()
