from typing import List, Union
from openai import AsyncOpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.client = None
        self.use_local = settings.USE_LOCAL_EMBEDDING
        self.local_model = None

        if self.use_local:
            try:
                # Lazy import to avoid hard dependency if not used
                from fastembed import TextEmbedding
                logger.info(f"Initializing local embedding model: {settings.LOCAL_EMBEDDING_MODEL}")
                self.local_model = TextEmbedding(model_name=settings.LOCAL_EMBEDDING_MODEL)
            except ImportError as e:
                logger.error(f"Failed to import fastembed runtime: {e}")
                logger.error("fastembed may be installed but its runtime dependency is unavailable. Please verify onnxruntime and Microsoft Visual C++ Redistributable.")
                self.use_local = False
            except Exception as e:
                logger.error(f"Error initializing local embedding model: {e}")
                self.use_local = False

        # Fallback or primary configuration for OpenAI API
        # Always initialize client if API Key is available to support runtime fallback
        if settings.EMBEDDING_API_KEY:
            try:
                self.client = AsyncOpenAI(
                    api_key=settings.EMBEDDING_API_KEY,
                    base_url=settings.EMBEDDING_BASE_URL
                )
                logger.info(f"Initialized OpenAI Embedding Client (Base URL: {settings.EMBEDDING_BASE_URL})")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI Client: {e}")
        else:
            if not self.use_local:
                logger.warning("Embedding API Key not configured and Local Embedding disabled. Semantic matching will be unavailable.")

    async def get_embedding(self, text: str) -> List[float]:
        # Ensure text is not empty
        if not text:
            return []
            
        # Replace newlines with spaces for better embedding quality
        text = text.replace("\n", " ")

        # 1. Try Local Embedding
        if self.use_local and self.local_model:
            try:
                # FastEmbed returns a generator of embeddings
                embeddings = list(self.local_model.embed([text]))
                if embeddings:
                    return embeddings[0].tolist()
            except Exception as e:
                logger.error(f"Error getting local embedding: {e}. Attempting fallback to Online Service.")
                # Do not raise here, let it fall through to Online

        # 2. Try Online Embedding (Fallback or Primary)
        if self.client:
            try:
                response = await self.client.embeddings.create(
                    input=[text],
                    model=settings.EMBEDDING_MODEL
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Error getting online embedding: {e}")
                raise
        
        # 3. No service available
        if self.use_local:
             raise RuntimeError("Local embedding failed and Online embedding not configured")
        raise ValueError("Embedding API Key not configured")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        cleaned_texts = [t.replace("\n", " ") for t in texts]

        # 1. Try Local Embedding
        if self.use_local and self.local_model:
            try:
                embeddings = list(self.local_model.embed(cleaned_texts))
                return [e.tolist() for e in embeddings]
            except Exception as e:
                logger.error(f"Error getting local embeddings: {e}. Attempting fallback to Online Service.")
                # Do not raise here, let it fall through to Online

        # 2. Try Online Embedding (Fallback or Primary)
        if self.client:
            try:
                # Batch processing could be implemented here if list is very large
                response = await self.client.embeddings.create(
                    input=cleaned_texts,
                    model=settings.EMBEDDING_MODEL
                )
                return [data.embedding for data in response.data]
            except Exception as e:
                logger.error(f"Error getting online embeddings: {e}")
                raise

        # 3. No service available
        if self.use_local:
             raise RuntimeError("Local embedding failed and Online embedding not configured")
        raise ValueError("Embedding API Key not configured")

embedding_service = EmbeddingService()
