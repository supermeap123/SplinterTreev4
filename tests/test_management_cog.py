import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
from cogs.management_cog import ManagementCog

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.get_cog.return_value = MagicMock()
    bot.api_client = MagicMock()
    return bot

@pytest.fixture
def cog(bot):
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"management": 0.5}'
        return ManagementCog(bot)

@pytest.fixture
def mock_message():
    message = MagicMock()
    message.channel.id = "123"
    message.id = "456"
    message.content = "Test message"
    message.author.id = "789"
    message.guild.id = "101112"
    message.guild = MagicMock()
    message.guild.name = "Test Server"
    message.channel.name = "test-channel"
    message.author.display_name = "TestUser"
    return message

def test_cog_initialization(cog):
    """Test the initialization of ManagementCog"""
    assert cog.name == "Management"
    assert cog.nickname == "Management"
    assert not cog.trigger_words  # Should be empty list
    assert cog.model == "meta-llama/llama-3.1-405b-instruct"
    assert cog.provider == "openrouter"
    assert cog.prompt_file == "None"
    assert not cog.supports_vision

def test_qualified_name(cog):
    """Test the qualified_name property"""
    assert cog.qualified_name == "Management"

def test_get_temperature(cog):
    """Test temperature settings"""
    # Test with temperature in settings
    cog.temperatures = {"management": 0.5}
    assert cog.get_temperature() == 0.5

    # Test with missing temperature
    cog.temperatures = {}
    assert cog.get_temperature() == 0.7  # Default temperature

@pytest.mark.asyncio
async def test_generate_response(cog, mock_message):
    """Test response generation"""
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

    # Test generate_response
    response = await cog.generate_response(mock_message)

    # Verify context messages were retrieved
    context_cog.get_context_messages.assert_called_once_with(
        "123",
        limit=50,
        exclude_message_id="456"
    )

    # Verify API was called with correct parameters
    api_client.call_openpipe.assert_called_once()
    call_args = api_client.call_openpipe.call_args[1]
    
    assert call_args["model"] == "meta-llama/llama-3.1-405b-instruct"
    assert call_args["provider"] == "openrouter"
    assert call_args["temperature"] == 0.5  # From mock temperatures.json
    assert call_args["stream"] == True
    assert call_args["prompt_file"] == "None"
    assert call_args["user_id"] == "789"
    assert call_args["guild_id"] == "101112"

    # Verify message formatting
    messages = call_args["messages"]
    assert len(messages) == 4  # system prompt + 2 history messages + current message
    assert messages[-1] == {"role": "user", "content": "Test message"}

    # Verify response
    assert response == "Test response"

@pytest.mark.asyncio
async def test_generate_response_error_handling(cog, mock_message):
    """Test error handling in generate_response"""
    # Mock context cog to raise exception
    context_cog = AsyncMock()
    context_cog.get_context_messages.side_effect = Exception("Test error")
    cog.context_cog = context_cog

    # Test error handling
    response = await cog.generate_response(mock_message)
    assert response is None

@pytest.mark.asyncio
async def test_handle_message(cog, mock_message):
    """Test message handling"""
    # Mock generate_response
    async def mock_generator():
        yield "Test response"
    cog.generate_response = AsyncMock(return_value=mock_generator())

    # Mock channel methods
    mock_message.channel.send = AsyncMock()
    mock_message.channel.typing = AsyncMock()
    mock_message.add_reaction = AsyncMock()

    # Test message handling
    await cog.handle_message(mock_message)

    # Verify typing indicator was started
    mock_message.channel.typing.assert_called_once()

    # Verify response was sent
    mock_message.channel.send.assert_called()

@pytest.mark.asyncio
async def test_temperature_file_handling(bot):
    """Test handling of temperatures.json file"""
    # Test with valid temperatures file
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"management": 0.5}'
        cog = ManagementCog(bot)
        assert cog.temperatures == {"management": 0.5}

    # Test with invalid temperatures file
    with patch('builtins.open', side_effect=Exception("File not found")):
        cog = ManagementCog(bot)
        assert cog.temperatures == {}

    # Test with invalid JSON in temperatures file
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = 'invalid json'
        cog = ManagementCog(bot)
        assert cog.temperatures == {}

@pytest.mark.asyncio
async def test_error_handling(cog, mock_message):
    """Test error handling in message processing"""
    # Mock generate_response to raise error
    cog.generate_response = AsyncMock(side_effect=Exception("Test error"))

    # Mock channel methods
    mock_message.channel.send = AsyncMock()
    mock_message.channel.typing = AsyncMock()

    # Test error handling
    await cog.handle_message(mock_message)

    # Verify error message was sent
    error_calls = [call for call in mock_message.channel.send.call_args_list if "Error" in str(call)]
    assert len(error_calls) > 0

@pytest.mark.asyncio
async def test_initialization(bot):
    """Test cog initialization"""
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        cog = ManagementCog(bot)
        
        # Verify basic attributes
        assert hasattr(cog, 'bot')
        assert hasattr(cog, 'api_client')
        assert hasattr(cog, 'temperatures')
        
        # Verify default values
        assert cog.name == "Management"
        assert cog.provider == "openrouter"
        assert not cog.supports_vision
