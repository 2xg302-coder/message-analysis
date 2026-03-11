import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default

class Settings:
    # LLM Settings (Main/Large Model - e.g. DeepSeek, OpenRouter High-end)
    # 支持多 Key 轮询：使用逗号分隔，例如 "key1,key2"
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    # 新增并发配置：LLM_CONCURRENCY="8,2" (对应 key1=8并发, key2=2并发)
    LLM_CONCURRENCY = os.getenv("LLM_CONCURRENCY", "8")

    # Fast/Small LLM Settings (Optional - e.g. Local Ollama, Gemini Flash)
    # If not set, will fallback to Main LLM in service layer or explicit fallback here
    FAST_LLM_API_KEY = os.getenv("FAST_LLM_API_KEY")
    FAST_LLM_BASE_URL = os.getenv("FAST_LLM_BASE_URL")
    FAST_LLM_MODEL = os.getenv("FAST_LLM_MODEL")
    FAST_LLM_CONCURRENCY = os.getenv("FAST_LLM_CONCURRENCY", "4")

    @property
    def LLM_CONFIGS(self):
        """Parse multiple API keys, base URLs, and models from env vars"""
        if not self.LLM_API_KEY:
            return []
        
        # Split by comma but allow "empty" strings for placeholder keys (like for local LLM)
        # But split() ignores empty strings if we strip.
        # Let's handle local LLM case: user might put "sk-123,local" or "sk-123,none"
        raw_keys = self.LLM_API_KEY.split(',')
        keys = [k.strip() for k in raw_keys] # keep empty ones? No, user should put a dummy value like 'none'
        
        # If BASE_URL is comma separated, split it. Else reuse single value.
        if self.LLM_BASE_URL and ',' in self.LLM_BASE_URL:
            urls = [u.strip() for u in self.LLM_BASE_URL.split(',') if u.strip()]
        else:
            urls = [self.LLM_BASE_URL] * len(keys) # Broadcast single URL
            
        # If MODEL is comma separated, split it. Else reuse single value.
        if self.LLM_MODEL and ',' in self.LLM_MODEL:
            models = [m.strip() for m in self.LLM_MODEL.split(',') if m.strip()]
        else:
            models = [self.LLM_MODEL] * len(keys) # Broadcast single Model

        # If CONCURRENCY is comma separated
        if self.LLM_CONCURRENCY and ',' in self.LLM_CONCURRENCY:
            concurrencies = [int(c.strip()) for c in self.LLM_CONCURRENCY.split(',') if c.strip()]
        else:
            try:
                default_conc = int(self.LLM_CONCURRENCY)
            except:
                default_conc = 8
            concurrencies = [default_conc] * len(keys)

        configs = []
        for i, key in enumerate(keys):
            # Use specific URL/Model if available, else fallback to last one (or single one)
            url = urls[i] if i < len(urls) else urls[-1]
            model = models[i] if i < len(models) else models[-1]
            concurrency = concurrencies[i] if i < len(concurrencies) else concurrencies[-1]
            
            # Handle 'none' or 'local' key for local LLM (no auth header needed ideally, but client requires one)
            real_key = key
            if key.lower() in ['none', 'local', 'empty']:
                real_key = 'sk-no-key-required'

            configs.append({
                "api_key": real_key,
                "base_url": url,
                "model": model,
                "concurrency": concurrency
            })
        return configs

    @property
    def FAST_LLM_CONFIGS(self):
        if not self.FAST_LLM_API_KEY:
            return []

        raw_keys = self.FAST_LLM_API_KEY.split(',')
        keys = [k.strip() for k in raw_keys if k.strip()]
        if not keys:
            return []

        if self.FAST_LLM_BASE_URL and ',' in self.FAST_LLM_BASE_URL:
            urls = [u.strip() for u in self.FAST_LLM_BASE_URL.split(',') if u.strip()]
        else:
            urls = [self.FAST_LLM_BASE_URL] * len(keys)

        if self.FAST_LLM_MODEL and ',' in self.FAST_LLM_MODEL:
            models = [m.strip() for m in self.FAST_LLM_MODEL.split(',') if m.strip()]
        else:
            models = [self.FAST_LLM_MODEL] * len(keys)

        if self.FAST_LLM_CONCURRENCY and ',' in self.FAST_LLM_CONCURRENCY:
            concurrencies = [int(c.strip()) for c in self.FAST_LLM_CONCURRENCY.split(',') if c.strip()]
        else:
            try:
                default_conc = int(self.FAST_LLM_CONCURRENCY)
            except:
                default_conc = 4
            concurrencies = [default_conc] * len(keys)

        configs = []
        for i, key in enumerate(keys):
            url = urls[i] if i < len(urls) else urls[-1]
            model = models[i] if i < len(models) else models[-1]
            concurrency = concurrencies[i] if i < len(concurrencies) else concurrencies[-1]
            real_key = key
            if key.lower() in ['none', 'local', 'empty', 'ollama']:
                real_key = 'sk-no-key-required'

            configs.append({
                "api_key": real_key,
                "base_url": url,
                "model": model,
                "concurrency": concurrency
            })
        return configs

    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "news.db"))
    
    # Sentiment Dictionary Paths
    POSITIVE_WORDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "positive_words.txt"))
    NEGATIVE_WORDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "negative_words.txt"))
    
    # API 认证配置
    # 如果设置了此值，则必须在请求头中携带 X-API-Key: YOUR_SECRET
    API_SECRET = os.getenv("API_SECRET")

    APP_STARTUP_BACKGROUND = _env_bool("APP_STARTUP_BACKGROUND", True)
    APP_STARTUP_DELAY_SECONDS = _env_int("APP_STARTUP_DELAY_SECONDS", 0)

    ANALYSIS_STARTUP_GRACE_SECONDS = _env_int("ANALYSIS_STARTUP_GRACE_SECONDS", 120)
    ANALYSIS_REALTIME_INTERVAL_SECONDS = _env_int("ANALYSIS_REALTIME_INTERVAL_SECONDS", 5)
    ANALYSIS_DAILY_BATCH_ENABLED = _env_bool("ANALYSIS_DAILY_BATCH_ENABLED", True)
    ANALYSIS_DAILY_BATCH_HOUR = _env_int("ANALYSIS_DAILY_BATCH_HOUR", 3)
    ANALYSIS_DAILY_BATCH_MINUTE = _env_int("ANALYSIS_DAILY_BATCH_MINUTE", 30)
    ANALYSIS_DAILY_BATCH_LIMIT = _env_int("ANALYSIS_DAILY_BATCH_LIMIT", 200)
    ANALYSIS_DAILY_BATCH_MODE = os.getenv("ANALYSIS_DAILY_BATCH_MODE", "fast")

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

    # QQ Bot Notification Settings
    # Mode: 'go-cqhttp' (default) or 'official' (QQ Official Bot)
    QQ_BOT_MODE = os.getenv("QQ_BOT_MODE", "go-cqhttp")
    
    # Common Settings
    NOTIFICATION_MIN_SCORE = _env_int("NOTIFICATION_MIN_SCORE", 7)

    # 1. go-cqhttp Settings
    QQ_BOT_API_URL = os.getenv("QQ_BOT_API_URL") # e.g. http://localhost:5700
    QQ_BOT_ACCESS_TOKEN = os.getenv("QQ_BOT_ACCESS_TOKEN")
    QQ_TARGET_GROUP_ID = os.getenv("QQ_TARGET_GROUP_ID") 
    QQ_TARGET_USER_ID = os.getenv("QQ_TARGET_USER_ID") 

    # 2. QQ Official Bot Settings
    # Get these from https://q.qq.com -> Developer Settings -> Robot Token
    QQ_BOT_APP_ID = os.getenv("QQ_BOT_APP_ID")
    QQ_BOT_TOKEN = os.getenv("QQ_BOT_TOKEN")
    # Channel ID (子频道 ID) - Essential for official bot notifications
    QQ_CHANNEL_ID = os.getenv("QQ_CHANNEL_ID")
    # Sandbox Mode (True/False)
    QQ_BOT_SANDBOX = _env_bool("QQ_BOT_SANDBOX", False)

settings = Settings()
