STORYLINE_SYSTEM_PROMPT = """你是一个专业的金融分析师。你的任务是从一天的财经日历中，识别出最可能影响市场的 3-5 个核心主线事件。忽略次要数据。"""

STORYLINE_USER_PROMPT_TEMPLATE = """这是今天的财经日历数据：
{calendar_data}

请输出 JSON 格式的主线列表，包含以下字段：
- title: 主线标题 (简洁明了)
- keywords: 关键词列表 (List[str])
- description: 详细描述，说明事件背景和可能的影响
- importance: 重要性 (1-5, 5为最高)
- expected_impact: 预期影响 (如：利多黄金, 利空美元, 市场波动加剧等)

JSON 结构示例:
{{
    "storylines": [
        {{
            "title": "美联储利率决议",
            "keywords": ["美联储", "加息", "FOMC"],
            "description": "...",
            "importance": 5,
            "expected_impact": "..."
        }}
    ]
}}
"""
