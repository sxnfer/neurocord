"""Embedding generation and management for semantic search."""

import asyncio
import logging
import math
from typing import List, Optional

import openai

from utils.config import get_config
from utils.models import OperationResult

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages text-to-vector embedding generation with OpenAI."""

    def __init__(self):
        """Initialize OpenAI client with configuration."""
        config = get_config()
        self.client = openai.AsyncOpenAI(api_key=config.openai_api_key)
        self.model = "text-embedding-3-small"  # Updated model from config
        self.batch_size = 10  # Your choice for reliability
        self.max_retries = 2  # Your choice for retry attempts

        logger.info(f"EmbeddingManager initialized with model: {self.model}")

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text with retry logic."""
        if not text or not text.strip():
            logger.warning("Empty text provided to generate_embedding")
            return None

        # Clean the text
        cleaned_text = text.strip()

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.embeddings.create(
                    model=self.model, input=[cleaned_text]
                )

                embedding = response.data[0].embedding
                logger.debug(
                    f"Generated embedding for text (length: {len(cleaned_text)})"
                )
                return embedding

            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    # Exponential backoff: 1s, 2s, 4s...
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error("Max retries exceeded for rate limiting")
                    return None

            except openai.APIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error("Max retries exceeded for API errors")
                    return None

            except Exception as e:
                logger.error(f"Unexpected error generating embedding: {e}")
                return None

        return None

    async def generate_embeddings_batch(
        self, texts: List[str]
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in batches of 10."""
        if not texts:
            return []

        # Clean and filter texts
        cleaned_texts = [text.strip() for text in texts if text and text.strip()]
        if not cleaned_texts:
            return [None] * len(texts)

        all_embeddings = []

        # Process in chunks of batch_size (10)
        for i in range(0, len(cleaned_texts), self.batch_size):
            batch = cleaned_texts[i : i + self.batch_size]

            for attempt in range(self.max_retries + 1):
                try:
                    response = await self.client.embeddings.create(
                        model=self.model, input=batch
                    )

                    # Extract embeddings in order
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)

                    logger.debug(
                        f"Generated {len(batch_embeddings)} embeddings in batch"
                    )
                    break

                except openai.RateLimitError as e:
                    logger.warning(
                        f"Batch rate limit hit on attempt {attempt + 1}: {e}"
                    )
                    if attempt < self.max_retries:
                        wait_time = 2**attempt
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Add None for failed batch
                        all_embeddings.extend([None] * len(batch))
                        break

                except Exception as e:
                    logger.error(f"Batch embedding error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(1)
                        continue
                    else:
                        # Add None for failed batch
                        all_embeddings.extend([None] * len(batch))
                        break

        return all_embeddings

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings (0-1 scale)."""
        if not embedding1 or not embedding2:
            return 0.0

        if len(embedding1) != len(embedding2):
            logger.error("Embedding dimensions don't match")
            return 0.0

        # Cosine similarity calculation
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        similarity = dot_product / (magnitude1 * magnitude2)

        # Convert from [-1, 1] to [0, 1] range
        return (similarity + 1) / 2

    async def test_connection(self) -> OperationResult:
        """Test OpenAI API connection."""
        try:
            test_embedding = await self.generate_embedding("test connection")

            if test_embedding:
                return OperationResult.success_result(
                    "OpenAI embedding service is working!",
                    data={"embedding_dimensions": len(test_embedding)},
                )
            else:
                return OperationResult.error_result("Failed to generate test embedding")

        except Exception as e:
            logger.error(f"Embedding service test failed: {e}")
            return OperationResult.error_result(
                "OpenAI API connection failed", errors=[str(e)]
            )


# Singleton instance for easy importing
embedding_manager = EmbeddingManager()
