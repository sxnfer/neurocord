"""Tests for Ask cog using OpenAI chat completions."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import nextcord
import openai
import pytest

from cogs.ask import Ask


@pytest.fixture
def bot():
    return MagicMock()


@pytest.fixture
def interaction():
    inter = MagicMock(spec=nextcord.Interaction)
    # Allow ask in DMs as well; include guild for logging
    inter.guild.id = 1111
    inter.user.id = 2222
    inter.response.defer = AsyncMock()
    inter.followup.send = AsyncMock()
    return inter


def _mock_openai_response(text: str):
    choice = MagicMock()
    message = MagicMock()
    message.content = text
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def make_cog():
    def _factory():
        with (
            patch("cogs.ask.get_config") as mock_get_config,
            patch("cogs.ask.openai.AsyncOpenAI") as mock_ai_ctor,
        ):
            mock_config = MagicMock()
            mock_config.openai_api_key = "test_openai_key_abcdefghijklmnopqrstuvwxyz"
            mock_get_config.return_value = mock_config

            mock_client = MagicMock()
            # Provide nested attribute for chat.completions.create
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=_mock_openai_response("Hello from AI!")
            )

            mock_ai_ctor.return_value = mock_client

            cog = Ask(bot=MagicMock(), model_name="gpt-5-mini")
            # Attach the mock client for further customization in tests
            cog.client = mock_client
            return cog, mock_client

    return _factory


@pytest.mark.asyncio
async def test_ask_success(make_cog, interaction):
    cog, client = make_cog()

    await cog.ask(interaction, prompt="What is Python?", private=True)

    interaction.response.defer.assert_called_once_with(ephemeral=True)
    interaction.followup.send.assert_called_once()
    args, kwargs = interaction.followup.send.call_args
    content_arg = args[0] if args else kwargs.get("content")
    assert "Hello from AI!" in content_arg
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_ask_public_response(make_cog, interaction):
    cog, client = make_cog()
    await cog.ask(interaction, prompt="Public reply", private=False)

    interaction.response.defer.assert_called_once_with(ephemeral=False)
    args, kwargs = interaction.followup.send.call_args
    assert kwargs.get("ephemeral") is False


@pytest.mark.asyncio
async def test_ask_fallback_model(make_cog, interaction):
    cog, client = make_cog()

    # First call raises APIError, second succeeds
    client.chat.completions.create.side_effect = [
        openai.APIError(
            message="model error",
            request=MagicMock(),
            body={"error": {"message": "model error"}},
        ),
        _mock_openai_response("Fallback response"),
    ]

    await cog.ask(interaction, prompt="Trigger fallback", private=True)

    # Ensure we attempted twice
    assert client.chat.completions.create.await_count == 2
    args, kwargs = interaction.followup.send.call_args
    content_arg = args[0] if args else kwargs.get("content")
    assert "Fallback response" in content_arg


@pytest.mark.asyncio
async def test_ask_empty_choices(make_cog, interaction):
    cog, client = make_cog()

    empty_response = MagicMock()
    empty_response.choices = []
    client.chat.completions.create.return_value = empty_response

    await cog.ask(interaction, prompt="anything", private=True)

    args, kwargs = interaction.followup.send.call_args
    content_arg = args[0] if args else kwargs.get("content")
    assert "couldn't generate a response" in content_arg.lower()


@pytest.mark.asyncio
async def test_ask_truncates_long_response(make_cog, interaction):
    cog, client = make_cog()

    long_text = "A" * 2100
    client.chat.completions.create.return_value = _mock_openai_response(long_text)

    await cog.ask(interaction, prompt="Long please", private=True)

    args, kwargs = interaction.followup.send.call_args
    content_arg = args[0] if args else kwargs.get("content")
    assert len(content_arg) <= 1900
    assert content_arg.endswith("… (truncated)")


@pytest.mark.asyncio
async def test_defer_failure_short_circuit(make_cog, interaction):
    cog, client = make_cog()
    interaction.response.defer.side_effect = Exception("Defer failed")

    await cog.ask(interaction, prompt="hi", private=True)

    # Should not attempt to send followup if defer failed and we returned early
    interaction.followup.send.assert_not_called()


# Test fixtures for pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
