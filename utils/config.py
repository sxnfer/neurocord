"""Configuration management with type safety and validation."""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """Type-safe configuration with validation."""

    # Discord configuration
    discord_token: str = Field(..., description="Discord bot token")

    # Database configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase service key")

    # OpenAI configuration
    openai_api_key: str = Field(..., description="OpenAI API key for embeddings")

    # Optional Watch2gether configuration
    watch2gether_api_key: Optional[str] = Field(
        None, description="Watch2gether API key"
    )

    # Bot configuration
    command_prefix: str = Field(default="!", description="Bot command prefix")
    max_search_results: int = Field(
        default=10, description="Maximum search results to return"
    )
    embedding_dimension: int = Field(
        default=1536, description="OpenAI embedding dimension"
    )

    @field_validator("discord_token")
    def validate_discord_token(cls, value: str) -> str:
        """Validate Discord token format."""
        if not value or len(value) < 50:
            raise ValueError("Discord token appears to be invalid")
        return value

    @field_validator("supabase_url")
    def validate_supabase_url(cls, value: str) -> str:
        """Validate Supabase URL format."""
        if not value.startswith("https://") or "supabase.co" not in value:
            raise ValueError("Supabase URL must be a valid https://...supabase.co URL")
        return value

    @field_validator("openai_api_key")
    def validate_openai_key(cls, value: str) -> str:
        """Validate OpenAI API key format."""
        if not value.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return value

    @field_validator("max_search_results")
    def validate_max_results(cls, value: int) -> int:
        """Validate search results limit."""
        if not 1 <= value <= 50:
            raise ValueError("max_search_results must be between 1 and 50")
        return value

    @classmethod
    def from_env(cls) -> "Config":
        """Factory method for environment-based configuration."""
        # Load .env file if it exists
        load_dotenv()

        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            watch2gether_api_key=os.getenv("WATCH2GETHER_API_KEY"),
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
            max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "10")),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
        )


# Global configuration instance
config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global config
    if config is None:
        config = Config.from_env()
    return config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global config
    config = Config.from_env()
    return config
