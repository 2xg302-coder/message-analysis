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
    "cooccurrence": {
        "graph": None,
        "clusters": None,
        "timestamp": None
    },
    "causal": {
        "graph": None,
        "clusters": None,
        "timestamp": None
    }
}
CACHE_TTL = 300  # 5 minutes

class EntityMiner:
    def __init__(self):
        self.graph = nx.Graph()

    def _extract_names_from_list(self, entities_list: list) -> List[str]:
        names = []
        for item in entities_list:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                if 'name' in item:
                    names.append(item['name'])
                else:
                    names.extend(item.keys())
        return names

    async def fetch_recent_entities(self, hours: int = 2) -> List[List[str]]:
        """
        Fetch news from the last N hours and extract entities.
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
            
            stmt = select(News.entities).where(News.time >= cutoff_str)
            
            entity_lists = []
            
            async with engine.connect() as conn:
                result = await conn.execute(stmt)
                rows = result.fetchall()
                
                for row in rows:
                    entities_json = row[0]
                    if not entities_json:
                        continue
                    
                    try:
                        # entities 字段存储为 JSON 字符串
                        if isinstance(entities_json, str):
                            if entities_json.startswith("'") or entities_json.startswith('"'):
                                pass
                            
                            entities_dict = json.loads(entities_json)
                            
                            if isinstance(entities_dict, dict):
                                entity_lists.append(list(entities_dict.keys()))
                            elif isinstance(entities_dict, list):
                                entity_lists.append(self._extract_names_from_list(entities_dict))
                        elif isinstance(entities_json, dict):
                             entity_lists.append(list(entities_json.keys()))
                        elif isinstance(entities_json, list):
                             entity_lists.append(self._extract_names_from_list(entities_json))
                            
                    except json.JSONDecodeError:
                        try:
                            import ast
                            entities_dict = ast.literal_eval(entities_json)
                            if isinstance(entities_dict, dict):
                                entity_lists.append(list(entities_dict.keys()))
                        except Exception:
                            pass
                    except Exception as e:
                        logger.error(f"Error processing entities row: {e}")
                        
            return entity_lists
        except Exception as e:
            logger.error(f"Error fetching recent entities: {e}")
            return []

    async def fetch_recent_triples(self, hours: int = 2) -> List[Dict[str, str]]:
        """
        Fetch news from the last N hours and extract triples.
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
        
        stmt = select(News.triples).where(News.time >= cutoff_str)
        
        triples_list = []
        
        try:
            async with engine.connect() as conn:
                result = await conn.execute(stmt)
                rows = result.fetchall()
                
                for row in rows:
                    triples_json = row[0]
                    if not triples_json:
                        continue
                    
                    try:
                        triples = json.loads(triples_json)
                        if isinstance(triples, list):
                            triples_list.extend(triples)
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        logger.error(f"Error processing triples: {e}")
                        
        except Exception as e:
            logger.error(f"Error fetching recent triples: {e}")
            
        return triples_list

    def build_cooccurrence_matrix(self, entity_lists: List[List[str]], min_weight: int = 3):
        """
        Build a co-occurrence graph from lists of entities.
        """
        self.graph = nx.Graph()
        
        edge_weights = {}
        
        for entities in entity_lists:
            if len(entities) < 2:
                continue
                
            sorted_entities = sorted(entities)
            
            for i in range(len(sorted_entities)):
                for j in range(i + 1, len(sorted_entities)):
                    u, v = sorted_entities[i], sorted_entities[j]
                    if u == v:
                        continue
                        
                    edge = (u, v)
                    edge_weights[edge] = edge_weights.get(edge, 0) + 1
        
        for (u, v), weight in edge_weights.items():
            if weight >= min_weight:
                self.graph.add_edge(u, v, weight=weight)
                
        logger.info(f"Built co-occurrence graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")

    def build_causal_graph(self, triples_list: List[Dict[str, str]], min_weight: int = 1):
        """
        Build a directed causal graph from triples.
        """
        self.graph = nx.DiGraph()
        
        # (u, v) -> {predicate: count}
        edge_data = {}
        
        for triple in triples_list:
            u = triple.get('subject')
            p = triple.get('predicate')
            v = triple.get('object')
            
            if not u or not v:
                continue
            
            # Simple cleaning
            u = u.strip()
            v = v.strip()
            if not p:
                p = "relates_to"
            else:
                p = p.strip()
                
            if u == v:
                continue
                
            key = (u, v)
            if key not in edge_data:
                edge_data[key] = {}
            edge_data[key][p] = edge_data[key].get(p, 0) + 1
            
        for (u, v), preds in edge_data.items():
            total_weight = sum(preds.values())
            if total_weight >= min_weight:
                # Find most common predicate
                most_common_pred = max(preds.items(), key=lambda x: x[1])[0]
                self.graph.add_edge(u, v, weight=total_weight, label=most_common_pred)
                
        logger.info(f"Built causal graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")

    def detect_communities(self) -> List[Dict[str, Any]]:
        """
        Detect communities using Louvain algorithm.
        Note: Louvain works on undirected graphs. For DiGraph, we convert to undirected for community detection.
        """
        if self.graph.number_of_nodes() == 0:
            return []
            
        try:
            # Convert to undirected for community detection if needed
            g_for_comm = self.graph
            if self.graph.is_directed():
                g_for_comm = self.graph.to_undirected()
            
            # Check if there are edges, louvain needs edges
            if g_for_comm.number_of_edges() == 0:
                # If no edges, each node is its own community
                communities = {}
                for i, node in enumerate(g_for_comm.nodes()):
                    communities[i] = [node]
            else:
                partition = community_louvain.best_partition(g_for_comm)
                communities = {}
                for node, comm_id in partition.items():
                    if comm_id not in communities:
                        communities[comm_id] = []
                    communities[comm_id].append(node)
            
            sorted_clusters = sorted(communities.values(), key=len, reverse=True)
            
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
        # Calculate degree (in+out for directed)
        degrees = dict(self.graph.degree(weight='weight'))
        
        for node in self.graph.nodes():
            degree = degrees.get(node, 0)
            nodes.append({
                "id": node, 
                "name": node, 
                "value": degree,
                "symbolSize": min(max(degree, 5), 50)  # Scale node size
            })
            
        links = []
        for u, v, data in self.graph.edges(data=True):
            link = {
                "source": u, 
                "target": v, 
                "value": data.get('weight', 1)
            }
            if 'label' in data:
                link["label"] = {"show": True, "formatter": data['label']}
                link["lineStyle"] = {"curveness": 0.2}
            
            links.append(link)
                 
        return {
            "nodes": nodes,
            "links": links,
            "type": "directed" if self.graph.is_directed() else "undirected"
        }

async def get_entity_miner_result(hours: int = 2, force_refresh: bool = False, graph_type: str = "cooccurrence"):
    global _cache
    now = datetime.now()
    
    if graph_type not in ["cooccurrence", "causal"]:
        graph_type = "cooccurrence"
    
    # Check cache
    cache_entry = _cache[graph_type]
    if not force_refresh and cache_entry["timestamp"] and (now - cache_entry["timestamp"]).total_seconds() < CACHE_TTL:
        if cache_entry["graph"] is not None:
            return cache_entry["graph"], cache_entry["clusters"]
        
    miner = EntityMiner()
    
    if graph_type == "cooccurrence":
        entity_lists = await miner.fetch_recent_entities(hours=hours)
        miner.build_cooccurrence_matrix(entity_lists)
    else: # causal
        triples_list = await miner.fetch_recent_triples(hours=hours)
        miner.build_causal_graph(triples_list)
        
    clusters = miner.detect_communities()
    graph_data = miner.get_graph_data()
    
    # Update cache
    _cache[graph_type]["graph"] = graph_data
    _cache[graph_type]["clusters"] = clusters
    _cache[graph_type]["timestamp"] = now
    
    return graph_data, clusters
