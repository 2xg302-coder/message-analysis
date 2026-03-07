import pytest
from unittest.mock import MagicMock, AsyncMock
from services.entity_miner import EntityMiner

@pytest.mark.asyncio
async def test_fetch_recent_entities(mocker):
    # Mock database connection and result
    mock_result = MagicMock()
    # Mock rows with entities JSON
    mock_result.fetchall.return_value = [
        ('{"A": "ORG", "B": "LOC"}',),
        ('{"B": "LOC", "C": "PER"}',),
        ('{"A": "ORG", "C": "PER"}',)
    ]
    
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result
    
    # Mock engine.connect context manager
    mock_engine_connect = mocker.patch('services.entity_miner.engine.connect')
    mock_engine_connect.return_value.__aenter__.return_value = mock_conn
    
    miner = EntityMiner()
    entities = await miner.fetch_recent_entities(hours=2)
    
    assert len(entities) == 3
    assert "A" in entities[0]
    assert "B" in entities[0]

def test_build_cooccurrence_matrix():
    miner = EntityMiner()
    entity_lists = [
        ["A", "B"],
        ["B", "C"],
        ["A", "C"],
        ["A", "B", "C"]
    ]
    
    # Use min_weight=1 to capture all edges
    miner.build_cooccurrence_matrix(entity_lists, min_weight=1)
    
    assert miner.graph.number_of_nodes() == 3
    assert miner.graph.has_edge("A", "B")
    assert miner.graph.has_edge("B", "C")
    assert miner.graph.has_edge("A", "C")
    
    # Check weights
    # A-B: 1 (list 0) + 1 (list 3) = 2
    assert miner.graph["A"]["B"]["weight"] == 2

def test_detect_communities():
    miner = EntityMiner()
    # Create a graph with two distinct communities: {A, B, C} and {X, Y, Z}
    # Connect within communities strongly, between them weakly or not at all
    
    # Community 1
    miner.graph.add_edge("A", "B", weight=10)
    miner.graph.add_edge("B", "C", weight=10)
    miner.graph.add_edge("A", "C", weight=10)
    
    # Community 2
    miner.graph.add_edge("X", "Y", weight=10)
    miner.graph.add_edge("Y", "Z", weight=10)
    miner.graph.add_edge("X", "Z", weight=10)
    
    clusters = miner.detect_communities()
    
    assert len(clusters) == 2
    # Check if A, B, C are in one cluster
    cluster1 = next((c for c in clusters if "A" in c["entities"]), None)
    assert cluster1 is not None
    assert "B" in cluster1["entities"]
    assert "C" in cluster1["entities"]
    assert "X" not in cluster1["entities"]

def test_get_graph_data():
    miner = EntityMiner()
    miner.graph.add_edge("A", "B", weight=5)
    
    data = miner.get_graph_data()
    
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) == 2
    assert len(data["links"]) == 1
    assert data["links"][0]["value"] == 5
