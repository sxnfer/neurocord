"""Data models for Discord bot semantic search functionality."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseEntity(BaseModel):
    """Base model for all domain entities."""

    id: Optional[UUID] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Pydantic v2 configuration
    model_config = ConfigDict(from_attributes=True)


class SemanticContent(BaseEntity):
    """Model for saved content with semantic embeddings."""

    user_id: int = Field(..., description="Discord user ID who saved the content")
    guild_id: int = Field(..., description="Discord guild ID where content was saved")
    content: str = Field(..., description="The actual text content")
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding of the content"
    )

    @field_validator("embedding", mode="before")
    def validate_embedding(cls, value):
        """Convert string embedding from database to list of floats."""
        if value is None:
            return None
        if isinstance(value, str):
            # Parse string representation like "[0.1, 0.2, 0.3]"
            try:
                # Remove brackets and split by comma
                if value.startswith("[") and value.endswith("]"):
                    value = value[1:-1]
                return [float(x.strip()) for x in value.split(",") if x.strip()]
            except (ValueError, AttributeError):
                return None
        if isinstance(value, list):
            return value
        return None

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
