from openai import AsyncOpenAI
import json
import itertools
from config import settings
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_PROMPT_TEMPLATE, FAST_ANALYSIS_SYSTEM_PROMPT, FAST_ANALYSIS_USER_PROMPT_TEMPLATE

clients = []
client_iterator = None

fast_client = None

# Initialize Main Clients (Multiple Keys Support)
llm_configs = settings.LLM_CONFIGS
if llm_configs:
    print(f"Initializing LLM Service with {len(llm_configs)} configurations...")
    for config in llm_configs:
        key = config["api_key"]
        if key and key != 'sk-your-key-here':
            client = AsyncOpenAI(
                api_key=key,
                base_url=config["base_url"]
            )
            # Store tuple of (client, model_name)
            clients.append({
                "client": client,
                "model": config["model"]
            })
    
    if clients:
        client_iterator = itertools.cycle(clients)
    else:
        print('Warning: No valid LLM API Keys found.')
else:
    print('Warning: LLM API Key not configured. Main Analysis will be skipped.')

# Initialize Fast Client (Small Model)
# If FAST_LLM_* is not configured, fallback to Main Client configuration logic (handled in call_llm wrapper or here)
if settings.FAST_LLM_API_KEY:
    fast_client = AsyncOpenAI(
        api_key=settings.FAST_LLM_API_KEY,
        base_url=settings.FAST_LLM_BASE_URL
    )

def get_next_client_config():
    if client_iterator:
        return next(client_iterator)
    return None

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_llm(messages: List[Dict[str, str]], timeout: float = 30.0, use_fast_model: bool = False) -> Dict[str, Any]:
    current_client = None
    model_name = None

    if use_fast_model and fast_client:
        current_client = fast_client
        model_name = settings.FAST_LLM_MODEL or settings.LLM_MODEL
    else:
        config = get_next_client_config()
        if config:
            current_client = config["client"]
            model_name = config["model"]
    
    if not current_client:
        # If fast client requested but not configured, try main client fallback
        if use_fast_model:
            config = get_next_client_config()
            if config:
                current_client = config["client"]
                model_name = config["model"] # Fallback to main model
            
    if not current_client:
        raise Exception("No API Key configured for the requested model type")
        
    response = await current_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
        timeout=timeout
    )
    
    content = response.choices[0].message.content
    # Clean up markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
        
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback cleanup
        content = content.strip().strip('`')
        return json.loads(content)

async def analyze_news(news_content: str, watchlist: List[str] = [], mode: str = "standard") -> Dict[str, Any]:
    if not clients and not fast_client:
        return {'error': 'No API Key'}

    watchlist_str = ", ".join(watchlist) if watchlist else "无"
    
    if mode == "fast":
        system_prompt = FAST_ANALYSIS_SYSTEM_PROMPT
        user_prompt = FAST_ANALYSIS_USER_PROMPT_TEMPLATE.format(content=news_content, watchlist=watchlist_str)
        timeout = 10.0 # Fast timeout
        use_fast_model = True
    else:
        system_prompt = ANALYSIS_SYSTEM_PROMPT
        user_prompt = ANALYSIS_USER_PROMPT_TEMPLATE.format(content=news_content, watchlist=watchlist_str)
        timeout = 45.0
        use_fast_model = False
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        return await call_llm(messages, timeout=timeout, use_fast_model=use_fast_model)
    except Exception as e:
        print(f'LLM Analysis Error (after retries): {e}')
        return {'error': str(e)}
