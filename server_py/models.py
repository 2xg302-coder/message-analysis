from pydantic import BaseModel
from typing import List, Dict, Optional

class NewsItem(BaseModel):
    id: str
    title: str
    content: str
    link: str
    time: str
    source: str
    type: str = "article"
    tags: List[str] = []
    entities: Dict[str, str] = {}
    impact_score: int = 0
    sentiment_score: float = 0.0
    simhash: Optional[str] = None
