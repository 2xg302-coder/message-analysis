import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings:
    # LLM Settings (Main/Large Model - e.g. DeepSeek, OpenRouter High-end)
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

    # Fast/Small LLM Settings (Optional - e.g. Local Ollama, Gemini Flash)
    # If not set, will fallback to Main LLM in service layer or explicit fallback here
    FAST_LLM_API_KEY = os.getenv("FAST_LLM_API_KEY")
    FAST_LLM_BASE_URL = os.getenv("FAST_LLM_BASE_URL")
    FAST_LLM_MODEL = os.getenv("FAST_LLM_MODEL")
    
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "news.db"))
    
    # Sentiment Dictionary Paths
    POSITIVE_WORDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "positive_words.txt"))
    NEGATIVE_WORDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "negative_words.txt"))
    
    # API 认证配置
    # 如果设置了此值，则必须在请求头中携带 X-API-Key: YOUR_SECRET
    API_SECRET = os.getenv("API_SECRET")

    # Embedding Settings
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY") or LLM_API_KEY
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL") or "https://api.openai.com/v1"
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Vector DB Path
    VECTOR_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "chroma_db"))

settings = Settings()
