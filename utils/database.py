"""Database operations for semantic search with Supabase and pgvector."""

import asyncio
import logging
from typing import Optional

from supabase import create_client, Client
from postgrest.exceptions import APIError
from utils.config import get_config
from utils.models import (
    OperationResult,
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

logger = logging.getLogger(__name__)


def database_timeout(operation_type: str):
    """Timeout decorator with comprehensive error handling."""
    timeout_seconds = OPERATION_TIMEOUTS.get(operation_type, 3)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                error_msg = f"Database {operation_type} took too long (>{timeout_seconds}s). Please try again."
                logger.warning(
                    f"Database timeout: {operation_type} exceeded {timeout_seconds}s"
                )
                return OperationResult.error_result(error_msg)
            except ConnectionError as e:
                error_msg = "Cannot connect to database. Please try again in a moment."
                logger.error(f"Database connection error in {operation_type}: {e}")
                return OperationResult.error_result(error_msg)
            except APIError as e:
                error_msg = f"Database error during {operation_type}. Please try again."
                logger.error(f"Supabase API error in {operation_type}: {e}")
                return OperationResult.error_result(error_msg)
            except Exception as e:
                error_msg = (
                    f"Unexpected error during {operation_type}. Please try again."
                )
                logger.error(f"Unexpected database error in {operation_type}: {e}")
                return OperationResult.error_result(error_msg)

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
            config = get_config()
            self._client = create_client(config.supabase_url, config.supabase_key)
            logger.info("Database manager initialized with connection pooling")

    @database_timeout("test")
    async def test_connection(self) -> OperationResult:
        """Test database connection and basic functionality."""
        try:
            # Simple query to test connection
            response = (
                self._client.table("semantic_content")
                .select("count")
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
            response = (
                self._client.table("semantic_content")
                .select("count")
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


# Singleton instance for easy importing
db_manager = DatabaseManager()
