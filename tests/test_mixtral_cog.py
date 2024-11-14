import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
from cogs.mixtral_cog import MixtralCog

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.get_cog.return_value = MagicMock()
    return bot

@pytest.fixture
def cog(bot):
    return MixtralCog(bot)

def test_cog_initialization(cog):
    assert cog.name == "Mixtral"
    assert cog.nickname == "Mixtral"
    assert cog.model == "mistralai/pixtral-12b"
    assert cog.provider == "openrouter"
    assert cog.trigger_words == ["mixtral"]
    assert not cog.supports_vision
    assert cog.prompt_file == "mixtral_prompts"

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
    context_cog.get_context_messages.return_value = [
        {
            'id': '123',
            'user_id': 'user1',
            'content': 'Previous message',
            'is_assistant': False
        },
        {
            'id': '124',
            'user_id': 'SYSTEM',
            'content': '[SUMMARY] Chat summary',
            'is_assistant': False
        }
    ]
    cog.context_cog = context_cog

    # Mock API client
    api_client = AsyncMock()
    api_client.call_openpipe.return_value = "Test response"
    cog.api_client = api_client

    # Mock temperature settings
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"mixtral": 0.8}'
        cog.temperatures = {"mixtral": 0.8}

    # Test generate_response
    response = await cog.generate_response(message)

    # Verify context messages were retrieved
    context_cog.get_context_messages.assert_called_once_with(
        "123",
        limit=50,
        exclude_message_id="456"
    )

    # Verify API was called with correct parameters
    api_client.call_openpipe.assert_called_once()
    call_args = api_client.call_openpipe.call_args[1]
    
    assert call_args["model"] == "mistralai/pixtral-12b"
    assert call_args["provider"] == "openrouter"
    assert call_args["temperature"] == 0.8
    assert call_args["stream"] == True
    assert call_args["prompt_file"] == "mixtral_prompts"
    assert call_args["user_id"] == "789"
    assert call_args["guild_id"] == "101112"

    # Verify message formatting
    messages = call_args["messages"]
    assert len(messages) == 4  # system prompt + 2 history messages + current message
    assert messages[-1] == {"role": "user", "content": "Test message"}

    # Verify response
    assert response == "Test response"

@pytest.mark.asyncio
async def test_generate_response_error_handling(cog):
    # Mock message
    message = MagicMock()
    message.channel.id = "123"
    message.id = "456"
    message.content = "Test message"
    message.author.id = "789"
    message.guild.id = "101112"

    # Mock context cog to raise exception
    context_cog = AsyncMock()
    context_cog.get_context_messages.side_effect = Exception("Test error")
    cog.context_cog = context_cog

    # Test error handling
    response = await cog.generate_response(message)
    assert response is None

def test_get_temperature(cog):
    # Test with temperature in settings
    cog.temperatures = {"mixtral": 0.8}
    assert cog.get_temperature() == 0.8

    # Test with missing temperature
    cog.temperatures = {}
    assert cog.get_temperature() == 0.7  # Default temperature

def test_qualified_name(cog):
    assert cog.qualified_name == "Mixtral"

@pytest.mark.asyncio
async def test_setup(bot):
    # Test successful setup
    cog = await MixtralCog.setup(bot)
    assert isinstance(cog, MixtralCog)
    bot.add_cog.assert_called_once()

    # Test setup failure
    bot.add_cog.side_effect = Exception("Setup failed")
    with pytest.raises(Exception):
        await MixtralCog.setup(bot)
