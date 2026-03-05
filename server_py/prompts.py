from typing import Dict, Any

ANALYSIS_SYSTEM_PROMPT = """你是一位资深金融数据分析师。你的任务是从财经新闻中提取结构化知识，进行情感分析和影响评估。
特别关注：
1. 宏观经济指标（如加息、降息、CPI、非农数据）
2. 地缘政治事件（如战争、制裁、外交冲突）
3. 大宗商品波动（如黄金、原油、有色金属）
4. 市场传闻与八卦（如未经证实的并购、高管变动、小道消息）

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
    "AAPL": "Apple",
    "XAU": "黄金", // 大宗商品
    "FED": "美联储" // 机构
  }},
  "tags": ["标签1", "标签2"], // 包含宏观标签（如：加息、地缘政治）
  "impact_score": 3, // 1-5 (1:微弱影响, 5:重大影响)
  "sentiment_score": 0.0, // -1.0 (极度负面) 到 1.0 (极度正面)
  "event_type": "其他", // 枚举值：业绩、并购、政策、宏观、人事、地缘政治、市场传闻、大宗商品、其他
  "reasoning": "简短的分析理由"
}}

参考示例 (Few-shot Examples):

Example 1 (宏观/加息):
Input: "美联储宣布加息25个基点，鲍威尔暗示未来可能暂停加息。"
Output: {{
  "summary": "美联储加息25基点，暗示可能暂停。",
  "entities": {{
    "FED": "美联储",
    "POWELL": "鲍威尔"
  }},
  "tags": ["加息", "货币政策", "美元"],
  "impact_score": 5,
  "sentiment_score": -0.2,
  "event_type": "宏观",
  "reasoning": "加息本身偏空，但暂停信号缓和了情绪。"
}}

Example 2 (地缘/战争/黄金):
Input: "中东局势升级，某国原油设施遇袭，国际金价短线拉升突破2000美元。"
Output: {{
  "summary": "中东局势升级引避险情绪，金价突破2000美元。",
  "entities": {{
    "XAU": "黄金",
    "OIL": "原油"
  }},
  "tags": ["地缘政治", "避险", "黄金", "原油"],
  "impact_score": 4,
  "sentiment_score": 0.6,
  "event_type": "地缘政治",
  "reasoning": "地缘冲突推高避险资产（黄金）和能源价格。"
}}

Example 3 (市场传闻/八卦):
Input: "市场传闻某头部券商将被并购，相关概念股午后异动。"
Output: {{
  "summary": "传闻头部券商将被并购，概念股异动。",
  "entities": {{
    "UNKNOWN": "某头部券商"
  }},
  "tags": ["并购传闻", "券商", "小作文"],
  "impact_score": 3,
  "sentiment_score": 0.4,
  "event_type": "市场传闻",
  "reasoning": "未经证实的并购传闻往往能短期提振板块情绪。"
}}
"""

FAST_ANALYSIS_SYSTEM_PROMPT = """你是一个高频交易系统的AI分析师。快速提取关键信息，JSON输出。"""

FAST_ANALYSIS_USER_PROMPT_TEMPLATE = """
新闻: "{content}"

输出JSON:
{{
  "tags": ["关键标签"],
  "entities": {{"代码": "名称"}},
  "event_type": "类型(宏观/公司/地缘/传闻/其他)",
  "impact_score": 3, // 1-5
  "sentiment_score": 0.0 // -1到1
}}
"""
