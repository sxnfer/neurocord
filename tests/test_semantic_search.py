"""Tests for Semantic Search cog flows and security guards."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import nextcord
import pytest

from cogs.semantic_search import SemanticSearch
from utils.models import OperationResult, SearchResult, SemanticContent


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def cog(bot):
    return SemanticSearch(bot)


@pytest.fixture
def interaction():
    inter = MagicMock(spec=nextcord.Interaction)
    inter.guild.id = 1111
    inter.user.id = 2222
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()
    return inter


@pytest.mark.asyncio
async def test_save_success(cog, interaction):
    with (
        patch("cogs.semantic_search.embedding_manager") as em,
        patch("cogs.semantic_search.db_manager") as db,
    ):
        em.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        db.save_content = AsyncMock(
            return_value=OperationResult.success_result(
                "Content saved successfully!", data={"id": str(uuid4())}
            )
        )

        await cog.save_content(interaction, content="This is some valid content text")

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "✅" in embed.title
        assert "Content Saved" in embed.title


@pytest.mark.asyncio
async def test_save_embedding_failure(cog, interaction):
    with patch("cogs.semantic_search.embedding_manager") as em:
        em.generate_embedding = AsyncMock(return_value=None)

        await cog.save_content(interaction, content="some content that fails")

        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "❌" in embed.title
        assert "Embedding Failed" in embed.title


@pytest.mark.asyncio
async def test_save_database_error(cog, interaction):
    with (
        patch("cogs.semantic_search.embedding_manager") as em,
        patch("cogs.semantic_search.db_manager") as db,
    ):
        em.generate_embedding = AsyncMock(return_value=[0.1, 0.2])
        db.save_content = AsyncMock(
            return_value=OperationResult.error_result("DB down")
        )

        await cog.save_content(interaction, content="another valid content string")

        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "❌" in embed.title
        assert "Save Failed" in embed.title
        assert "DB down" in embed.description


@pytest.mark.asyncio
async def test_search_success(cog, interaction):
    with (
        patch("cogs.semantic_search.embedding_manager") as em,
        patch("cogs.semantic_search.db_manager") as db,
    ):
        em.generate_embedding = AsyncMock(return_value=[0.3, 0.4, 0.5])

        c1 = SemanticContent(
            id=uuid4(),
            user_id=3333,
            guild_id=interaction.guild.id,
            content="First saved note for testing",
            embedding=None,
            created_at=datetime.now(UTC),
        )
        c2 = SemanticContent(
            id=uuid4(),
            user_id=4444,
            guild_id=interaction.guild.id,
            content="Second item, more content here",
            embedding=None,
            created_at=datetime.now(UTC),
        )
        db.search_content = AsyncMock(
            return_value=[
                SearchResult(content=c1, similarity_score=0.9),
                SearchResult(content=c2, similarity_score=0.7),
            ]
        )

        await cog.search_content(interaction, query="saved note", limit=5)

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "🔍" in embed.title
        assert "Search Results" in embed.title
        # Should have two result fields
        assert len(embed.fields) >= 2


@pytest.mark.asyncio
async def test_search_no_results(cog, interaction):
    with (
        patch("cogs.semantic_search.embedding_manager") as em,
        patch("cogs.semantic_search.db_manager") as db,
    ):
        em.generate_embedding = AsyncMock(return_value=[0.9])
        db.search_content = AsyncMock(return_value=[])

        await cog.search_content(interaction, query="unknown", limit=3)

        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "No Results" in embed.title


@pytest.mark.asyncio
async def test_search_guild_only_guard(cog):
    # Interaction without a guild should receive an ephemeral notice
    inter = MagicMock(spec=nextcord.Interaction)
    inter.guild = None
    inter.user.id = 2222
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()

    with patch("cogs.semantic_search.embedding_manager") as em:
        em.generate_embedding = AsyncMock()

        await cog.search_content(inter, query="anything", limit=1)

        # Ensure we send an ephemeral guard message
        inter.followup.send.assert_called_once()
        call = inter.followup.send.call_args
        args, kwargs = call.args, call.kwargs
        assert kwargs.get("ephemeral") is True
        # Content may be passed positionally or via kwarg; support both
        msg = None
        if args and isinstance(args[0], str):
            msg = args[0]
        else:
            msg = kwargs.get("content")
        if msg is not None:
            assert "only be used in servers" in msg
        elif "embed" in kwargs:
            assert "only be used in servers" in kwargs["embed"].description


@pytest.mark.asyncio
async def test_delete_success(cog, interaction):
    with patch("cogs.semantic_search.db_manager") as db:
        db.delete_content = AsyncMock(
            return_value=OperationResult.success_result("Deleted!")
        )

        cid = str(uuid4())
        await cog.delete_content(interaction, content_id=cid)

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "✅" in embed.title
        assert "Deleted" in embed.title


@pytest.mark.asyncio
async def test_delete_invalid_id(cog, interaction):
    await cog.delete_content(interaction, content_id="not-a-uuid")
    embed = interaction.followup.send.call_args.kwargs["embed"]
    assert "❌" in embed.title
    assert "Invalid ID" in embed.title


@pytest.mark.asyncio
async def test_edit_success(cog, interaction):
    with (
        patch("cogs.semantic_search.embedding_manager") as em,
        patch("cogs.semantic_search.db_manager") as db,
    ):
        em.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        db.edit_content = AsyncMock(
            return_value=OperationResult.success_result("Updated!")
        )

        cid = str(uuid4())
        await cog.edit_content(
            interaction, content_id=cid, new_content="Updated content string"
        )

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "✅" in embed.title
        assert "Updated" in embed.title


@pytest.mark.asyncio
async def test_edit_embedding_failure(cog, interaction):
    with patch("cogs.semantic_search.embedding_manager") as em:
        em.generate_embedding = AsyncMock(return_value=None)

        await cog.edit_content(
            interaction, content_id=str(uuid4()), new_content="fails"
        )

        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "❌" in embed.title
        assert "Embedding Failed" in embed.title


@pytest.mark.asyncio
async def test_my_content_list(cog, interaction):
    items = [
        SemanticContent(
            id=uuid4(),
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            content="Some long content to preview in embed",
            created_at=datetime.now(UTC),
        ),
        SemanticContent(
            id=uuid4(),
            user_id=interaction.user.id,
            guild_id=interaction.guild.id,
            content="Another saved item",
            created_at=datetime.now(UTC),
        ),
    ]

    with patch("cogs.semantic_search.db_manager") as db:
        db.get_user_content = AsyncMock(return_value=items)

        await cog.my_content(interaction)

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        embed = interaction.followup.send.call_args.kwargs["embed"]
        assert "📝" in embed.title
        assert "Your Saved Content" in embed.title
        assert len(embed.fields) >= 2


# Test fixtures for pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
