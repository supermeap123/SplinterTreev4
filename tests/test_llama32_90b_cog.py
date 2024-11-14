import pytest
from cogs.llama32_90b_cog import Llama3290bVisionCog
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_bot():
    return MagicMock()

@pytest.fixture
def cog(mock_bot):
    return Llama3290bVisionCog(mock_bot)

def test_cog_initialization(cog):
    assert cog.name == "Llama-3.2-90B-Vision"
    assert cog.nickname == "Llama Vision"
    assert cog.model == "meta-llama/llama-3.2-90b-vision-instruct"
    assert cog.provider == "openrouter"
    assert cog.supports_vision == False

@pytest.mark.asyncio
async def test_generate_response(cog):
    message = MagicMock()
    message.content = "Test message"
    message.channel.id = 123
    message.id = 456
    message.author.id = 789
    message.guild.id = 101112

    cog.api_client.call_openpipe = AsyncMock(return_value="response_stream")
    cog.context_cog.get_context_messages = AsyncMock(return_value=[])

    response = await cog.generate_response(message)
    assert response == "response_stream"
