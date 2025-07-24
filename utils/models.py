"""Data models for Discord bot semantic search functionality."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base model for all domain entities."""

    id: Optional[UUID] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class SemanticContent(BaseEntity):
    """Model for saved content with semantic embeddings."""

    user_id: int = Field(..., description="Discord user ID who saved the content")
    guild_id: int = Field(..., description="Discord guild ID where content was saved")
    content: str = Field(..., description="The actual text content")
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding of the content"
    )

    @property
    def content_preview(self) -> str:
        """Get a shortened preview of the content."""
        if len(self.content) <= 100:
            return self.content
        return self.content[:97] + "..."


class SearchResult(BaseModel):
    """Model for search results with similarity scores."""

    content: SemanticContent = Field(..., description="The matched content")
    similarity_score: float = Field(..., description="Cosine similarity score (0-1)")

    @property
    def percentage_match(self) -> float:
        """Convert similarity score to percentage."""
        return self.similarity_score * 100


class SearchQuery(BaseModel):
    """Model for search query parameters."""

    query: str = Field(..., description="Search query text")
    user_id: int = Field(..., description="Discord user ID performing search")
    guild_id: int = Field(..., description="Discord guild ID to search within")
    limit: int = Field(default=5, description="Maximum number of results")
    min_similarity: float = Field(
        default=0.1, description="Minimum similarity threshold"
    )


class WatchRoom(BaseEntity):
    """Model for Watch2gether rooms."""

    guild_id: int = Field(..., description="Discord guild ID (primary key)")
    room_url: str = Field(..., description="Watch2gether room URL")
    created_by: int = Field(..., description="Discord user ID who created the room")

    @property
    def is_expired(self) -> bool:
        """Check if room is older than 24 hours."""
        if not self.created_at:
            return True
        return (datetime.utcnow() - self.created_at).total_seconds() > 86400  # 24 hours


class OperationResult(BaseModel):
    """Standard result wrapper for operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Operation result data")
    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )

    @classmethod
    def success_result(
        self, message: str = "Operation completed successfully", data: Any = None
    ) -> "OperationResult":
        """Factory for success results."""
        return self(success=True, message=message, data=data, errors=[])

    @classmethod
    def error_result(
        self,
        message: str = "Operation failed",
        errors: Optional[List[str]] = None,
        data: Any = None,
    ) -> "OperationResult":
        """Factory for error results."""
        return self(success=False, message=message, data=data, errors=errors or [])


class EmbeddingRequest(BaseModel):
    """Model for embedding generation requests."""

    text: str = Field(..., description="Text to generate embedding for")
    model: str = Field(
        default="text-embedding-3-small	", description="OpenAI embedding model"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "text": "How to use semantic search in Discord",
                "model": "text-embedding-ada-002",
            }
        }


class EmbeddingResponse(BaseModel):
    """Model for embedding generation responses."""

    embedding: List[float] = Field(..., description="Generated embedding vector")
    token_count: int = Field(..., description="Number of tokens processed")
    model_used: str = Field(..., description="Model used for generation")


class ContentValidation(BaseModel):
    """Model for content validation results."""

    is_valid: bool = Field(..., description="Whether content passes validation")
    content_length: int = Field(..., description="Length of content in characters")
    word_count: int = Field(..., description="Number of words in content")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    @classmethod
    def validate_content(self, content: str) -> "ContentValidation":
        """Validate content for saving."""
        errors = []
        warnings = []

        # Check minimum length
        if len(content.strip()) < 10:
            errors.append("Content must be at least 10 characters long")

        # Check maximum length
        if len(content) > 4000:
            errors.append("Content cannot exceed 4000 characters")

        # Check for very long content
        if len(content) > 2000:
            warnings.append("Very long content may affect search performance")

        # Count words
        word_count = len(content.split())
        if word_count < 3:
            errors.append("Content must contain at least 3 words")

        return self(
            is_valid=len(errors) == 0,
            content_length=len(content),
            word_count=word_count,
            errors=errors,
            warnings=warnings,
        )
