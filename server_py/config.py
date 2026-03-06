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
    # 默认尝试使用本地模型 (FastEmbed/BGE)，若失败则回退到在线 API
    USE_LOCAL_EMBEDDING = os.getenv("USE_LOCAL_EMBEDDING", "true").lower() == "true"
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY") or LLM_API_KEY
    # 在线 Embedding 接口地址。若国内无法访问 OpenAI，请配置国内兼容接口 (如 SiliconFlow, DeepSeek, Zhipu 等)
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL") or "https://api.openai.com/v1"
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
    
    # Vector DB Path
    VECTOR_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "chroma_db"))

settings = Settings()
