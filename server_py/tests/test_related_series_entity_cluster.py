import json
from collections import Counter
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.news_service import NewsService


def test_build_entity_clusters_merge_alias_and_substring():
    service = NewsService(database=MagicMock())
    all_entities = {"美国", "USA", "美 国", "乌克兰", "乌克兰局势", "以色列"}
    frequency = Counter({"美国": 5, "USA": 2, "美 国": 1, "乌克兰": 3, "乌克兰局势": 1, "以色列": 2})

    canonical_map, _ = service._build_entity_clusters(all_entities, frequency)

    assert canonical_map["USA"] == "美国"
    assert canonical_map["美 国"] == "美国"
    assert canonical_map["乌克兰局势"] == "乌克兰"


@pytest.mark.asyncio
async def test_get_related_series_dedup_shared_entities():
    service = NewsService(database=MagicMock())
    service.get_news_by_series = AsyncMock(return_value=[
        {"analysis": {"entities": ["美国", "USA", "乌克兰"]}}
    ])
    service.get_series_list = AsyncMock(return_value=[
        {"tag": "中东冲突", "count": 20, "latest_date": "2026-03-10T10:00:00"},
        {"tag": "中东局势", "count": 10, "latest_date": "2026-03-10T09:00:00"},
        {"tag": "俄乌冲突", "count": 8, "latest_date": "2026-03-10T08:00:00"}
    ])

    rows = [
        {"analysis": json.dumps({"event_tag": "中东局势", "entities": ["United States", "乌克兰局势", "伊朗"]}, ensure_ascii=False)},
        {"analysis": json.dumps({"event_tag": "俄乌冲突", "entities": ["乌克兰", "俄罗斯"]}, ensure_ascii=False)}
    ]
    service.db.execute_query = AsyncMock(return_value=rows)

    related = await service.get_related_series("中东冲突", limit=5)

    assert len(related) >= 1
    first = related[0]
    assert "shared_entities" in first
    assert "美国" in first["shared_entities"]
    assert "USA" not in first["shared_entities"]
