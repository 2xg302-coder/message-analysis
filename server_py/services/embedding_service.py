from typing import List, Union
from openai import AsyncOpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.client = None
        if settings.EMBEDDING_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.EMBEDDING_API_KEY,
                base_url=settings.EMBEDDING_BASE_URL
            )
        else:
            logger.warning("Embedding API Key not configured. Semantic matching will be disabled.")

    async def get_embedding(self, text: str) -> List[float]:
        if not self.client:
            raise ValueError("Embedding API Key not configured")
        
        # Ensure text is not empty and truncated if necessary (OpenAI limits)
        if not text:
            return []
            
        try:
            # Replace newlines with spaces for better embedding quality
            text = text.replace("\n", " ")
            
            response = await self.client.embeddings.create(
                input=[text],
                model=settings.EMBEDDING_MODEL
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.client:
            raise ValueError("Embedding API Key not configured")
            
        if not texts:
            return []
            
        try:
            # Batch processing could be implemented here if list is very large
            # For now, simple implementation
            cleaned_texts = [t.replace("\n", " ") for t in texts]
            
            response = await self.client.embeddings.create(
                input=cleaned_texts,
                model=settings.EMBEDDING_MODEL
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise

embedding_service = EmbeddingService()
