"""Database operations for semantic search with Supabase and pgvector."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from postgrest.exceptions import APIError
from supabase import Client, create_client

from utils.config import get_config
from utils.logging_config import get_logger, log_performance
from utils.models import (
    ContentValidation,
    OperationResult,
    SearchResult,
    SemanticContent,
)

# Operation timeout configuration (your idea!)
OPERATION_TIMEOUTS = {
    "search": 5,  # Most used, can be complex
    "save": 3,  # Quick operation
    "delete": 2,  # Simple operation
    "edit": 4,  # Moderate complexity
    "batch_save": 8,  # Complex, less frequent
    "test": 3,  # Connection testing
}

logger = get_logger("database")


def database_timeout(operation_type: str, fallback=None):
    """Timeout decorator with comprehensive error handling and typed fallbacks.

    If a fallback is provided, it will be returned on timeout/connection/API errors.
    Fallback can be a value or a zero-arg callable returning the value.
    """
    timeout_seconds = OPERATION_TIMEOUTS.get(operation_type, 3)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except (asyncio.TimeoutError, ConnectionError, APIError) as e:
                logger.warning(
                    f"Database {operation_type} error/timeout after {timeout_seconds}s: {e}"
                )
                if callable(fallback):
                    return fallback()
                return fallback
            except Exception as e:
                logger.error(
                    f"Unexpected database error in {operation_type}: {e}",
                )
                if callable(fallback):
                    return fallback()
                return fallback

        return wrapper

    return decorator


class DatabaseManager:
    """Singleton database manager for semantic search operations."""

    _instance = None
    _client: Optional[Client] = None

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Supabase client with connection pooling."""
        if self._client is None:
            init_start = time.time()
            config = get_config()
            self._client = create_client(config.supabase_url, config.supabase_key)
            init_duration = time.time() - init_start

            log_performance("database_client_init", init_duration)
            logger.info("Database manager initialized with connection pooling")

    @database_timeout(
        "test",
        fallback=lambda: OperationResult.error_result(
            "Database connection failed (timeout)"
        ),
    )
    async def test_connection(self) -> OperationResult:
        """Test database connection and basic functionality."""
        try:
            # Simple query to test connection
            await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .select("*")
                .limit(1)
                .execute()
            )

            return OperationResult.success_result(
                "Database connection successful!",
                data={"status": "connected", "response_time": "< 3s"},
            )
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return OperationResult.error_result(
                "Database connection failed. Please check your configuration.",
                errors=[str(e)],
            )

    async def health_check(self) -> dict:
        """Get database health information."""
        try:
            # Test basic table access
            await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .select("*")
                .limit(1)
                .execute()
            )

            return {
                "status": "healthy",
                "connection": "active",
                "tables_accessible": True,
                "message": "Database is ready for operations",
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "connection": "failed",
                "tables_accessible": False,
                "message": f"Database error: {str(e)}",
            }

    @database_timeout(
        "save",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while saving content"
        ),
    )
    async def save_content(
        self, content: str, embedding: List[float], user_id: int, guild_id: int
    ) -> OperationResult:
        """Save content with vector embedding to database."""
        # Validate content using our model
        validation = ContentValidation.validate_content(content)
        if not validation.is_valid:
            return OperationResult.error_result(
                "Content validation failed", errors=validation.errors
            )

        try:
            # Insert content with embedding
            now = datetime.now(timezone.utc).isoformat()
            response = await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .insert(
                    {
                        "user_id": user_id,
                        "guild_id": guild_id,
                        "content": content.strip(),
                        "embedding": embedding,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                .execute()
            )

            if response.data:
                saved_content = SemanticContent(**response.data[0])
                logger.info(f"Saved content for user {user_id} in guild {guild_id}")
                return OperationResult.success_result(
                    "Content saved successfully!", data={"id": str(saved_content.id)}
                )
            else:
                return OperationResult.error_result("Failed to save content")

        except Exception as e:
            logger.error(f"Error saving content: {e}")
            return OperationResult.error_result(
                "Database error while saving content", errors=[str(e)]
            )

    @database_timeout("search", fallback=list)
    async def search_content(
        self,
        query_embedding: List[float],
        guild_id: int,
        limit: int = 10,
        min_similarity: float = 0.1,
    ) -> List[SearchResult]:
        """Vector similarity search with recency tiebreaker."""
        try:
            # Convert similarity threshold to distance threshold
            # Cosine distance = 1 - cosine similarity
            max_distance = 1.0 - min_similarity

            # Execute vector similarity search using Supabase's RPC function
            response = await asyncio.to_thread(
                lambda: self._client.rpc(
                    "match_semantic_content",
                    {
                        "query_embedding": query_embedding,
                        "match_guild_id": guild_id,
                        "match_threshold": max_distance,
                        "match_count": limit,
                    },
                ).execute()
            )

            results = []
            for row in response.data or []:
                # Convert distance back to similarity
                similarity = 1.0 - row.get("distance", 1.0)

                # Create SemanticContent object
                content = SemanticContent(
                    id=row["id"],
                    user_id=row["user_id"],
                    guild_id=row["guild_id"],
                    content=row["content"],
                    embedding=row.get("embedding"),
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at"),
                )

                # Create SearchResult
                results.append(
                    SearchResult(content=content, similarity_score=similarity)
                )

            logger.info(
                f"Found {len(results)} similar content items for guild {guild_id}"
            )
            return results

        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return []

    @database_timeout(
        "delete",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while deleting content"
        ),
    )
    async def delete_content(self, content_id: UUID, user_id: int) -> OperationResult:
        """Delete content with owner validation."""
        try:
            # First, check if the content exists and user owns it
            response = await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .select("user_id, content")
                .eq("id", str(content_id))
                .execute()
            )

            if not response.data:
                return OperationResult.error_result("Content not found")

            content_data = response.data[0]
            if content_data["user_id"] != user_id:
                return OperationResult.error_result(
                    "You can only delete your own content"
                )

            # Delete the content
            await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .delete()
                .eq("id", str(content_id))
                .execute()
            )

            logger.info(f"Deleted content {content_id} by user {user_id}")
            return OperationResult.success_result("Content deleted successfully!")

        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            return OperationResult.error_result(
                "Database error while deleting content", errors=[str(e)]
            )

    @database_timeout(
        "edit",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while updating content"
        ),
    )
    async def edit_content(
        self,
        content_id: UUID,
        new_content: str,
        new_embedding: List[float],
        user_id: int,
    ) -> OperationResult:
        """Edit content and update embedding."""
        # Validate new content
        validation = ContentValidation.validate_content(new_content)
        if not validation.is_valid:
            return OperationResult.error_result(
                "Content validation failed", errors=validation.errors
            )

        try:
            # First, check if the content exists and user owns it
            response = await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .select("user_id")
                .eq("id", str(content_id))
                .execute()
            )

            if not response.data:
                return OperationResult.error_result("Content not found")

            if response.data[0]["user_id"] != user_id:
                return OperationResult.error_result(
                    "You can only edit your own content"
                )

            # Update the content and embedding
            now = datetime.now(timezone.utc).isoformat()
            update_response = await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .update(
                    {
                        "content": new_content.strip(),
                        "embedding": new_embedding,
                        "updated_at": now,  # Manual update
                    }
                )
                .eq("id", str(content_id))
                .execute()
            )

            if update_response.data:
                logger.info(f"Updated content {content_id} by user {user_id}")
                return OperationResult.success_result("Content updated successfully!")
            else:
                return OperationResult.error_result("Failed to update content")

        except Exception as e:
            logger.error(f"Error updating content: {e}")
            return OperationResult.error_result(
                "Database error while updating content", errors=[str(e)]
            )

    @database_timeout(
        "batch_save",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while batch saving content"
        ),
    )
    async def batch_save_content(
        self, content_list: List[Dict[str, Any]]
    ) -> OperationResult:
        """Save multiple contents efficiently in a single transaction."""
        if not content_list:
            return OperationResult.error_result("No content provided for batch save")

        # Validate all content first
        validation_errors = []
        for i, item in enumerate(content_list):
            validation = ContentValidation.validate_content(item.get("content", ""))
            if not validation.is_valid:
                validation_errors.append(
                    f"Item {i + 1}: {', '.join(validation.errors)}"
                )

        if validation_errors:
            return OperationResult.error_result(
                "Batch validation failed", errors=validation_errors
            )

        try:
            # Prepare batch data with timestamps
            batch_data = []
            for item in content_list:
                batch_data.append(
                    {
                        "user_id": item["user_id"],
                        "guild_id": item["guild_id"],
                        "content": item["content"].strip(),
                        "embedding": item["embedding"],
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )

            # Execute batch insert
            response = await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .insert(batch_data)
                .execute()
            )

            if response.data:
                saved_count = len(response.data)
                logger.info(f"Batch saved {saved_count} content items")
                return OperationResult.success_result(
                    f"Successfully saved {saved_count} items!",
                    data={"saved_count": saved_count},
                )
            else:
                return OperationResult.error_result("Failed to save batch content")

        except Exception as e:
            logger.error(f"Error in batch save: {e}")
            return OperationResult.error_result(
                "Database error during batch save", errors=[str(e)]
            )

    @database_timeout("search", fallback=list)
    async def get_user_content(
        self, user_id: int, guild_id: int, limit: int = 50
    ) -> List[SemanticContent]:
        """Get all content saved by a specific user in a guild."""
        try:
            # Query user's content directly (no vector search needed)
            response = await asyncio.to_thread(
                lambda: self._client.table("semantic_content")
                .select("*")
                .eq("user_id", user_id)
                .eq("guild_id", guild_id)
                .order("created_at", desc=True)  # Most recent first
                .limit(limit)
                .execute()
            )

            # Convert to SemanticContent objects
            user_content = []
            for row in response.data or []:
                content = SemanticContent(
                    id=row["id"],
                    user_id=row["user_id"],
                    guild_id=row["guild_id"],
                    content=row["content"],
                    embedding=row.get(
                        "embedding"
                    ),  # Will be converted by field validator
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at"),
                )
                user_content.append(content)

            logger.info(
                f"Retrieved {len(user_content)} content items for user {user_id}"
            )
            return user_content

        except Exception as e:
            logger.error(f"Error retrieving user content: {e}")
            return []

    @database_timeout("search", fallback=lambda: None)
    async def get_active_watch_room(self, guild_id: int) -> Optional[dict]:
        """Get active watch room for guild if it exists and is within 24 hours."""
        try:
            # Calculate 24 hours ago
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

            # Query for active room within 24 hours
            response = await asyncio.to_thread(
                lambda: self._client.table("watch_rooms")
                .select("*")
                .eq("guild_id", guild_id)
                .gte("created_at", twenty_four_hours_ago.isoformat())
                .execute()
            )

            if response.data:
                room_data = response.data[0]
                # Convert created_at string back to datetime
                room_data["created_at"] = datetime.fromisoformat(
                    room_data["created_at"].replace("Z", "+00:00")
                )
                logger.info(f"Found active room for guild {guild_id}")
                return room_data

            logger.info(f"No active room found for guild {guild_id}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving active watch room: {e}")
            return None

    @database_timeout(
        "save",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while saving watch room"
        ),
    )
    async def save_watch_room(
        self, guild_id: int, room_url: str, created_by: int
    ) -> OperationResult:
        """Save or update watch room for guild."""
        try:
            # Use upsert to handle both new rooms and room updates for same guild
            now = datetime.now(timezone.utc).isoformat()
            response = await asyncio.to_thread(
                lambda: self._client.table("watch_rooms")
                .upsert(
                    {
                        "guild_id": guild_id,
                        "room_url": room_url,
                        "created_at": now,
                        "created_by": created_by,
                    },
                    on_conflict="guild_id",
                )
                .execute()
            )

            if response.data:
                logger.info(f"Saved watch room for guild {guild_id}")
                return OperationResult.success_result(
                    "Watch room saved successfully!",
                    data={"guild_id": guild_id, "room_url": room_url},
                )
            else:
                return OperationResult.error_result("Failed to save watch room")

        except Exception as e:
            logger.error(f"Error saving watch room: {e}")
            return OperationResult.error_result(
                "Database error while saving watch room", errors=[str(e)]
            )

    @database_timeout(
        "delete",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while cleaning up watch room"
        ),
    )
    async def cleanup_invalid_watch_room(self, guild_id: int) -> OperationResult:
        """Clean up invalid watch room for a specific guild immediately."""
        try:
            # Delete the room for this guild
            await asyncio.to_thread(
                lambda: self._client.table("watch_rooms")
                .delete()
                .eq("guild_id", guild_id)
                .execute()
            )

            logger.info(f"Cleaned up invalid watch room for guild {guild_id}")
            return OperationResult.success_result(
                "Invalid room cleaned up", data={"guild_id": guild_id}
            )

        except Exception as e:
            logger.error(f"Error cleaning up invalid room for guild {guild_id}: {e}")
            return OperationResult.error_result(
                "Error during invalid room cleanup", errors=[str(e)]
            )

    @database_timeout(
        "delete",
        fallback=lambda: OperationResult.error_result(
            "Database operation timed out while cleaning up expired watch rooms"
        ),
    )
    async def cleanup_expired_watch_rooms(self) -> OperationResult:
        """Clean up watch rooms older than 24 hours (optional maintenance)."""
        try:
            # Calculate 24 hours ago
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

            # Delete expired rooms
            await asyncio.to_thread(
                lambda: self._client.table("watch_rooms")
                .delete()
                .lt("created_at", twenty_four_hours_ago.isoformat())
                .execute()
            )

            # Count is not directly available, but we can log the operation
            logger.info("Cleaned up expired watch rooms")
            return OperationResult.success_result("Expired rooms cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up expired rooms: {e}")
            return OperationResult.error_result("Error during cleanup", errors=[str(e)])


# Singleton instance for easy importing
db_manager = DatabaseManager()
