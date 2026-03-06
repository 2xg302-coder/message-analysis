import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import networkx as nx
import community as community_louvain
from sqlalchemy import text
from sqlmodel import select

from core.database_orm import engine
from core.logging import get_logger
from models_orm import News

logger = get_logger("entity_miner")

# Cache mechanism - simple in-memory cache
_cache = {
    "graph": None,
    "clusters": None,
    "timestamp": None
}
CACHE_TTL = 300  # 5 minutes

class EntityMiner:
    def __init__(self):
        self.graph = nx.Graph()

    async def fetch_recent_entities(self, hours: int = 2) -> List[List[str]]:
        """
        Fetch news from the last N hours and extract entities.
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 使用 ORM 查询，避免直接写 SQL 导致的时间格式兼容问题
        # 假设 time 字段是 ISO 格式字符串，可以直接进行字符串比较
        stmt = select(News.entities).where(News.time >= cutoff_str)
        
        entity_lists = []
        
        try:
            async with engine.connect() as conn:
                result = await conn.execute(stmt)
                rows = result.fetchall()
                
                for row in rows:
                    entities_json = row[0]
                    if not entities_json:
                        continue
                    
                    try:
                        # entities 字段存储为 JSON 字符串，例如 '{"Entity1": "Type1", "Entity2": "Type2"}'
                        # 或者如果是单引号的字符串表示，可能需要处理
                        if entities_json.startswith("'") or entities_json.startswith('"'):
                             # 如果已经是 JSON 字符串，直接加载
                             pass
                        
                        # 尝试解析
                        # 注意：如果数据库里存的是 Python 的 dict 字符串表示 (例如 {'a': 1})，json.loads 会失败
                        # 这里假设是标准的 JSON 格式。如果是 Python repr，可能需要 ast.literal_eval，但不安全。
                        # 根据 models_orm.py，默认是 "{}"，应该是 JSON。
                        entities_dict = json.loads(entities_json)
                        
                        if isinstance(entities_dict, dict):
                            # 我们只关心实体名称（键）
                            entity_lists.append(list(entities_dict.keys()))
                        elif isinstance(entities_dict, list):
                            # 以前可能是 list
                            entity_lists.append(entities_dict)
                            
                    except json.JSONDecodeError:
                        # 尝试处理 Python 字典字符串格式 (单引号)
                        try:
                            import ast
                            entities_dict = ast.literal_eval(entities_json)
                            if isinstance(entities_dict, dict):
                                entity_lists.append(list(entities_dict.keys()))
                        except Exception:
                            # logger.warning(f"Failed to decode entities JSON: {entities_json[:50]}...")
                            pass
                    except Exception as e:
                        logger.error(f"Error processing entities: {e}")
                        
        except Exception as e:
            logger.error(f"Error fetching recent entities: {e}")
            
        return entity_lists

    def build_cooccurrence_matrix(self, entity_lists: List[List[str]], min_weight: int = 3):
        """
        Build a co-occurrence graph from lists of entities.
        """
        self.graph = nx.Graph()
        
        # Count co-occurrences
        edge_weights = {}
        
        for entities in entity_lists:
            # Filter out single entities or empty lists
            if len(entities) < 2:
                continue
                
            # Sort to ensure consistent edge pairs (A, B) instead of (B, A)
            sorted_entities = sorted(entities)
            
            for i in range(len(sorted_entities)):
                for j in range(i + 1, len(sorted_entities)):
                    u, v = sorted_entities[i], sorted_entities[j]
                    if u == v:
                        continue
                        
                    edge = (u, v)
                    edge_weights[edge] = edge_weights.get(edge, 0) + 1
        
        # Add edges to graph if weight >= min_weight
        for (u, v), weight in edge_weights.items():
            if weight >= min_weight:
                self.graph.add_edge(u, v, weight=weight)
                
        logger.info(f"Built graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")

    def detect_communities(self) -> List[Dict[str, Any]]:
        """
        Detect communities using Louvain algorithm.
        Returns a list of clusters, each containing a list of entities.
        """
        if self.graph.number_of_nodes() == 0:
            return []
            
        try:
            partition = community_louvain.best_partition(self.graph)
            
            communities = {}
            for node, comm_id in partition.items():
                if comm_id not in communities:
                    communities[comm_id] = []
                communities[comm_id].append(node)
            
            # Convert to list of dicts for API response
            # Sort clusters by size (number of entities)
            sorted_clusters = sorted(communities.values(), key=len, reverse=True)
            
            # Format result
            result = []
            for i, entities in enumerate(sorted_clusters):
                result.append({
                    "id": i,
                    "entities": entities,
                    "size": len(entities)
                })
                
            return result
        except Exception as e:
            logger.error(f"Error detecting communities: {e}")
            return []

    def get_graph_data(self) -> Dict[str, Any]:
        """
        Return graph data in a format suitable for frontend visualization (e.g., ECharts).
        """
        nodes = []
        for node in self.graph.nodes():
            degree = self.graph.degree(node, weight='weight')
            nodes.append({
                "id": node, 
                "name": node, 
                "value": degree,
                "symbolSize": min(max(degree, 5), 50)  # Scale node size
            })
            
        links = []
        for u, v, data in self.graph.edges(data=True):
            links.append({
                "source": u, 
                "target": v, 
                "value": data['weight']
            })
                 
        return {
            "nodes": nodes,
            "links": links
        }

async def get_entity_miner_result(hours: int = 2, force_refresh: bool = False):
    global _cache
    now = datetime.now()
    
    # Check cache
    if not force_refresh and _cache["timestamp"] and (now - _cache["timestamp"]).total_seconds() < CACHE_TTL:
        if _cache["graph"] is not None:
            return _cache["graph"], _cache["clusters"]
        
    miner = EntityMiner()
    entity_lists = await miner.fetch_recent_entities(hours=hours)
    miner.build_cooccurrence_matrix(entity_lists)
    clusters = miner.detect_communities()
    graph_data = miner.get_graph_data()
    
    # Update cache
    _cache["graph"] = graph_data
    _cache["clusters"] = clusters
    _cache["timestamp"] = now
    
    return graph_data, clusters
