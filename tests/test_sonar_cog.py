import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
from cogs.sonar_cog import SonarCog

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.get_cog.return_value = MagicMock()
    return bot

@pytest.fixture
def cog(bot):
    return SonarCog(bot)

def test_cog_initialization(cog):
    assert cog.name == "Sonar"
    assert cog.nickname == "Sonar"
    assert cog.model == "perplexity/llama-3.1-sonar-large-128k-online"
    assert cog.provider == "openrouter"
    assert cog.trigger_words == ["sonar"]
    assert not cog.supports_vision

@pytest.mark.asyncio
async def test_generate_response(cog):
    # Mock message
    message = MagicMock()
    message.channel.id = "123"
    message.id = "456"
    message.content = "Test message"
    message.author.id = "789"
    message.guild.id = "101112"

    # Mock context cog
    context_cog = AsyncMock()
    context_cog.get_context_messages.return_value = []
    cog.context_cog = context_cog

    # Mock API client
    api_client = AsyncMock()
    api_client.call_openpipe.return_value = "Test response"
    cog.api_client = api_client

    # Test generate_response
    response = await cog.generate_response(message)

    # Verify API was called with correct parameters
    api_client.call_openpipe.assert_called_once()
    call_args = api_client.call_openpipe.call_args[1]
    
    assert call_args["model"] == "perplexity/llama-3.1-sonar-large-128k-online"
    assert call_args["provider"] == "openrouter"
    assert call_args["stream"] == True
    assert call_args["prompt_file"] == "sonar_prompts"
    assert call_args["user_id"] == "789"
    assert call_args["guild_id"] == "101112"

    # Verify response
    assert response == "Test response"
