import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "news.db"))
    
    # Sentiment Dictionary Paths
    POSITIVE_WORDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "positive_words.txt"))
    NEGATIVE_WORDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "negative_words.txt"))

settings = Settings()
