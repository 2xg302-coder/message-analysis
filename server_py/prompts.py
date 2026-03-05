from typing import Dict, Any

ANALYSIS_SYSTEM_PROMPT = """你是一位资深金融数据分析师。你的任务是从财经新闻中提取结构化知识，进行情感分析和影响评估。
请严格按照要求的 JSON 格式输出，不要包含 Markdown 代码块标记。
"""

ANALYSIS_USER_PROMPT_TEMPLATE = """
请对以下新闻内容进行深度分析：

新闻内容：
"{content}"

要求输出严格的 JSON 格式：
{{
  "summary": "新闻的 30 字以内精炼摘要",
  "entities": {{
    "股票代码(如有)": "实体名称",
    "AAPL": "Apple"
  }},
  "tags": ["标签1", "标签2"],
  "impact_score": 3, // 1-5 (1:微弱影响, 5:重大影响)
  "sentiment_score": 0.0, // -1.0 (极度负面) 到 1.0 (极度正面)
  "event_type": "其他", // 枚举值：业绩、并购、政策、宏观、人事、其他
  "reasoning": "简短的分析理由"
}}

参考示例 (Few-shot Examples):

Example 1 (利好):
Input: "贵州茅台发布公告，预计2023年净利润同比增长19%，超市场预期。"
Output: {{
  "summary": "贵州茅台预计2023年净利润增长19%，超预期。",
  "entities": {{
    "600519": "贵州茅台"
  }},
  "tags": ["业绩预告", "白酒", "消费"],
  "impact_score": 4,
  "sentiment_score": 0.8,
  "event_type": "业绩",
  "reasoning": "业绩超预期，明显的利好消息。"
}}

Example 2 (利空):
Input: "某某公司因涉嫌信披违规被证监会立案调查，股价跌停。"
Output: {{
  "summary": "某某公司涉嫌信披违规被立案调查。",
  "entities": {{
    "000000": "某某公司"
  }},
  "tags": ["立案调查", "监管"],
  "impact_score": 5,
  "sentiment_score": -0.9,
  "event_type": "政策",
  "reasoning": "监管立案通常对股价有重大负面影响。"
}}

Example 3 (中性):
Input: "万科A将于下周召开年度股东大会，审议董事会报告等议案。"
Output: {{
  "summary": "万科A将召开年度股东大会。",
  "entities": {{
    "000002": "万科A"
  }},
  "tags": ["股东大会"],
  "impact_score": 2,
  "sentiment_score": 0.0,
  "event_type": "其他",
  "reasoning": "常规公司治理活动，无明显多空方向。"
}}
"""
