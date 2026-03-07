from openai import AsyncOpenAI
import json
from config import settings
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_PROMPT_TEMPLATE, FAST_ANALYSIS_SYSTEM_PROMPT, FAST_ANALYSIS_USER_PROMPT_TEMPLATE

client = None
fast_client = None

# Initialize Main Client (Large Model)
if settings.LLM_API_KEY and settings.LLM_API_KEY != 'sk-your-key-here':
    client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL
    )
else:
    print('Warning: LLM API Key not configured. Main Analysis will be skipped.')

# Initialize Fast Client (Small Model)
# If FAST_LLM_* is not configured, fallback to Main Client configuration logic (handled in call_llm wrapper or here)
if settings.FAST_LLM_API_KEY:
    fast_client = AsyncOpenAI(
        api_key=settings.FAST_LLM_API_KEY,
        base_url=settings.FAST_LLM_BASE_URL
    )
else:
    fast_client = client # Fallback to main client

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_llm(messages: List[Dict[str, str]], timeout: float = 30.0, use_fast_model: bool = False) -> Dict[str, Any]:
    current_client = fast_client if use_fast_model and fast_client else client
    
    # Determine model name
    if use_fast_model and settings.FAST_LLM_MODEL:
        model_name = settings.FAST_LLM_MODEL
    else:
        model_name = settings.LLM_MODEL

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
    if not client and not fast_client:
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
