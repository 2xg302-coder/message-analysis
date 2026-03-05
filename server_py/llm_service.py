from openai import AsyncOpenAI
import json
from config import settings
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_PROMPT_TEMPLATE

client = None

if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != 'sk-your-key-here':
    client = AsyncOpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL
    )
else:
    print('Warning: DeepSeek API Key not configured. Analysis will be skipped.')

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_llm(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    if not client:
        raise Exception("No API Key configured")
        
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"}
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

async def analyze_news(news_content: str, existing_tags: List[str] = []) -> Dict[str, Any]:
    if not client:
        return {'error': 'No API Key'}

    # Note: existing_tags logic is temporarily removed to focus on strict structure compliance
    # If context is needed, we can inject it into the prompt template.
    
    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": ANALYSIS_USER_PROMPT_TEMPLATE.format(content=news_content)}
    ]

    try:
        return await call_llm(messages)
    except Exception as e:
        print(f'LLM Analysis Error (after retries): {e}')
        return {'error': str(e)}
