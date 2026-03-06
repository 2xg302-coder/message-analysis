STORYLINE_SYSTEM_PROMPT = """你是一个专业的金融分析师。你的任务是从一天的财经日历中，识别出最可能影响市场的 3-5 个核心主线事件。忽略次要数据。"""

STORYLINE_USER_PROMPT_TEMPLATE = """这是今天的财经日历数据：
{calendar_data}

这是最近 7 天的活跃市场主线（供参考，用于判断是否为连续剧）：
{history_data}

请输出 JSON 格式的主线列表，包含以下字段：
- title: 主线标题 (简洁明了)
- keywords: 关键词列表 (List[str])
- description: 详细描述，说明事件背景和可能的影响
- importance: 重要性 (1-5, 5为最高)
- expected_impact: 预期影响 (如：利多黄金, 利空美元, 市场波动加剧等)
- related_event_indices: 本条主线关联的财经日历事件索引列表 (从 0 开始，对应上方提供的日历数据顺序)
- parent_id: 如果这条主线是历史主线的延续，请填写对应的历史主线 ID (整数)；如果是新主线，请填 null

JSON 结构示例:
{{
    "storylines": [
        {{
            "title": "美联储利率决议",
            "keywords": ["美联储", "加息", "FOMC"],
            "description": "...",
            "importance": 5,
            "expected_impact": "...",
            "related_event_indices": [0, 2],
            "parent_id": 123
        }}
    ]
}}
"""
