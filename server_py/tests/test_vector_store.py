import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Ensure server_py is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.vector_store import VectorStore
# EmbeddingService is imported inside VectorStore, so we patch it there

@pytest.fixture
def mock_embedding_service():
    with patch('services.vector_store.embedding_service') as mock:
        mock.get_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        yield mock

@pytest.fixture
def mock_chroma_client():
    with patch('chromadb.PersistentClient') as mock_client:
        mock_collection = MagicMock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        yield mock_client

@pytest.mark.asyncio
async def test_add_storylines(mock_chroma_client, mock_embedding_service):
    # Initialize with mocked client
    with patch('services.vector_store.settings') as mock_settings:
        mock_settings.VECTOR_DB_PATH = "./test_db"
        vector_store = VectorStore()
        # Ensure collection is our mock
        vector_store.collection = MagicMock()
        
        storylines = [
            {"id": 1, "title": "Test Story 1", "description": "Desc 1"},
            {"id": 2, "title": "Test Story 2", "description": "Desc 2"}
        ]
        
        await vector_store.add_storylines(storylines)
        
        mock_embedding_service.get_embeddings.assert_called_once()
        vector_store.collection.upsert.assert_called_once()
        
        args, kwargs = vector_store.collection.upsert.call_args
        assert kwargs['ids'] == ['1', '2']
        assert len(kwargs['embeddings']) == 2
        assert len(kwargs['documents']) == 2

@pytest.mark.asyncio
async def test_query_news_tags(mock_chroma_client, mock_embedding_service):
    with patch('services.vector_store.settings') as mock_settings:
        mock_settings.VECTOR_DB_PATH = "./test_db"
        vector_store = VectorStore()
        
        # Mock query result
        # ids=[['1', '2']], distances=[[0.1, 0.8]], metadatas=[[{'id': 1, 'title': 'S1'}, {'id': 2, 'title': 'S2'}]]
        vector_store.collection = MagicMock()
        vector_store.collection.query.return_value = {
            'ids': [['1', '2']],
            'distances': [[0.1, 0.8]], # 0.1 means similarity 0.9, 0.8 means similarity 0.2
            'metadatas': [[{'id': 1, 'title': 'S1'}, {'id': 2, 'title': 'S2'}]]
        }
        
        matches = await vector_store.query_news_tags("some news", threshold=0.5)
        
        assert len(matches) == 1
        assert matches[0]['id'] == 1
        assert matches[0]['title'] == 'S1'
        # Float comparison with tolerance
        assert abs(matches[0]['score'] - 0.9) < 0.0001
    
        mock_embedding_service.get_embedding.assert_called_once_with("some news")

def test_clear_storylines(mock_chroma_client):
    with patch('services.vector_store.settings') as mock_settings:
        mock_settings.VECTOR_DB_PATH = "./test_db"
        vector_store = VectorStore()
        vector_store.client = MagicMock()
        
        vector_store.clear_storylines()
        
        vector_store.client.delete_collection.assert_called_once_with("storylines")
        vector_store.client.get_or_create_collection.assert_called_with(name="storylines", metadata={"hnsw:space": "cosine"})
