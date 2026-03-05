from openai import OpenAI
import json
from config import settings
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

client = None

if settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != 'sk-your-key-here':
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL
    )
else:
    # Use standard ASCII characters to avoid encoding issues on Windows consoles
    print('Warning: DeepSeek API Key not configured. Analysis will be skipped.')

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def call_llm(prompt: str) -> Dict[str, Any]:
    if not client:
        raise Exception("No API Key configured")
        
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    # Clean up markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
        
    return json.loads(content)

async def analyze_news(news_content: str, existing_tags: List[str] = []) -> Dict[str, Any]:
    if not client:
        return {'error': 'No API Key'}

    tags_context = ""
    if existing_tags:
        # Extract just the tags for context
        tag_names = [t['tag'] for t in existing_tags if isinstance(t, dict) and 'tag' in t]
        if not tag_names and existing_tags and isinstance(existing_tags[0], str):
            tag_names = existing_tags
            
        if tag_names:
            tags_context = f"""
### 现有活跃事件标签 (参考):
{json.dumps(tag_names, ensure_ascii=False)}

指令: 如果新闻与上述任何现有标签相关，请优先使用现有标签以保持事件脉络连贯性。
"""

    prompt = f"""
你是一位资深金融数据分析师。你的任务是从杂乱的财经新闻中提取高价值的结构化知识，并将其归类到特定的事件脉络中。

请对以下新闻内容进行分析：
"{news_content}"

{tags_context}

### 分析步骤与要求：
1. **去噪与价值判断**：
   - 首先判断该新闻是否包含实质性财经信息。
   - 如果是广告、纯水文、重复推广或无关内容，请将 score 设为 0，reasoning 说明原因，其他字段留空或设为 null。
   - 如果包含有价值信息，score 根据重要性打分 (1-10)。

2. **知识抽取与事件归类 (仅针对有价值新闻)**：
   - **summary**: 一句话摘要（<50字），客观陈述核心事实，不带感情色彩。
   - **score**: 市场影响力评分 (0-10)。
   - **event_tag**: 核心事件标签（例如："OpenAI人事变动", "美联储加息", "宁德时代财报"）。该标签将用于将多条相关新闻串联成连续剧，请保持标签的一致性和概括性。
   - **topic**: 主题关键词（例如："人工智能", "宏观经济", "新能源汽车"）。
   - **entities**: 提取文中提及的关键实体，格式为 [{{"name": "实体名", "type": "Company/Person/Org/Location", "code": "股票代码(如有)"}}]。
   - **event_type**: 事件类型 (如: 财报业绩, 监管政策, 市场动态, 人事变动, 并购重组, 新品发布, 其他)。
   - **key_facts**: 提取关键数据事实，格式为 [{{"key": "指标名称", "value": "数值/内容", "unit": "单位(如有)"}}]。例如：营收、净利润、涨跌幅、裁员人数等。
   - **impact**: 简述对哪些行业或概念板块有直接影响。

请直接返回 JSON 格式，不要包含 Markdown 格式标记（如 ```json）。确保 JSON 格式合法。
"""

    try:
        return call_llm(prompt)
    except Exception as e:
        print(f'LLM Analysis Error (after retries): {e}')
        return {'error': str(e)}
