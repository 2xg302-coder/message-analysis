import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
import logging
import os
from config import settings
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        try:
            # Ensure directory exists
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            
            self.client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
            # Use cosine similarity for better semantic matching
            self.collection = self.client.get_or_create_collection(
                name="storylines",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Vector Store initialized at {settings.VECTOR_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    async def add_storylines(self, storylines: List[Dict]):
        """
        Add storylines to vector store.
        storylines: List of dicts with 'id', 'title', 'description' (optional)
        """
        if not self.collection:
            logger.warning("Vector store not initialized")
            return

        if not storylines:
            return

        # Prepare data
        ids = [str(s['id']) for s in storylines]
        documents = [f"{s['title']}\n{s.get('description', '')}" for s in storylines]
        metadatas = [{"id": s['id'], "title": s['title']} for s in storylines]

        try:
            # Generate embeddings
            embeddings = await embedding_service.get_embeddings(documents)
            
            if embeddings:
                # Upsert to update existing or add new
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                logger.info(f"Upserted {len(storylines)} storylines to vector store")
        except Exception as e:
            logger.error(f"Error adding storylines to vector store: {e}")

    async def query_news_tags(self, news_text: str, n_results: int = 3, threshold: float = 0.4) -> List[Dict]:
        """
        Query vector store for matching storylines.
        Returns list of matched storylines with score.
        threshold: Minimum similarity score (0-1), default 0.4 for cosine similarity
        """
        if not self.collection:
            return []

        if not news_text:
            return []

        try:
            # Generate embedding for query
            embedding = await embedding_service.get_embedding(news_text)
            
            if not embedding:
                return []

            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results
            )
            
            # Process results
            matches = []
            if results['ids'] and results['distances']:
                ids = results['ids'][0]
                distances = results['distances'][0]
                metadatas = results['metadatas'][0]
                
                for i, dist in enumerate(distances):
                    # Chroma cosine distance: 0 is identical, 1 is orthogonal, 2 is opposite.
                    # Convert to similarity: 1 - dist
                    similarity = 1 - dist
                    
                    if similarity >= threshold:
                        matches.append({
                            "id": metadatas[i]['id'],
                            "title": metadatas[i]['title'],
                            "score": similarity
                        })
            
            if matches:
                logger.info(f"Found {len(matches)} matches for news")
                
            return matches

        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return []

    def clear_storylines(self):
        if self.client:
            try:
                self.client.delete_collection("storylines")
                self.collection = self.client.get_or_create_collection(
                    name="storylines",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("Cleared storylines vector store")
            except Exception as e:
                logger.error(f"Error clearing vector store: {e}")

vector_store = VectorStore()
