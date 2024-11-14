import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
from cogs.router_cog import RouterCog

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.get_cog.return_value = MagicMock()
    bot.api_client = MagicMock()
    return bot

@pytest.fixture
def cog(bot):
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"router": 0.5}'
        return RouterCog(bot)

@pytest.fixture
def mock_message():
    message = MagicMock()
    message.channel.id = "123"
    message.id = "456"
    message.content = "Test message"
    message.author.id = "789"
    message.guild.id = "101112"
    message.attachments = []
    return message

def test_cog_initialization(cog):
    """Test the initialization of RouterCog"""
    assert cog.name == "Router"
    assert cog.nickname == "Router"
    assert cog.model == "mistralai/ministral-3b"
    assert cog.provider == "openrouter"
    assert cog.prompt_file == "router"
    assert not cog.supports_vision

def test_qualified_name(cog):
    """Test the qualified_name property"""
    assert cog.qualified_name == "Router"

def test_get_temperature(cog):
    """Test temperature settings"""
    # Test with temperature in settings
    cog.temperatures = {"router": 0.5}
    assert cog.get_temperature() == 0.5

    # Test with missing temperature
    cog.temperatures = {}
    assert cog.get_temperature() == 0.7  # Default temperature

def test_normalize_model_name(cog):
    """Test model name normalization"""
    # Test exact matches
    assert cog.normalize_model_name("Mixtral") == "Mixtral"
    assert cog.normalize_model_name("Gemini") == "Gemini"

    # Test case variations
    assert cog.normalize_model_name("mixtral") == "Mixtral"
    assert cog.normalize_model_name("MIXTRAL") == "Mixtral"

    # Test common variations
    assert cog.normalize_model_name("ministral") == "Ministral"
    assert cog.normalize_model_name("ministral") == "Ministral"
    assert cog.normalize_model_name("gpt4") == "Liquid"  # Fallback
    assert cog.normalize_model_name("gpt-4") == "Liquid"  # Fallback

    # Test unknown model
    assert cog.normalize_model_name("unknown") == "Liquid"

def test_check_routing_loop(cog):
    """Test routing loop detection"""
    channel_id = "123"
    
    # Initialize routing history
    cog.routing_history = {}
    
    # First use should not be a loop
    assert not cog.check_routing_loop(channel_id, "Mixtral")
    assert channel_id in cog.last_model_used
    
    # Second consecutive use should not be a loop
    assert not cog.check_routing_loop(channel_id, "Mixtral")
    
    # Third consecutive use should be a loop
    assert cog.check_routing_loop(channel_id, "Mixtral")

    # Different model should reset the count
    assert not cog.check_routing_loop(channel_id, "Gemini")

def test_has_bypass_keywords(cog):
    """Test bypass keyword detection"""
    # Test direct model mentions
    assert cog.has_bypass_keywords("!mixtral hello")
    assert cog.has_bypass_keywords("use gemini for this")
    assert cog.has_bypass_keywords("switch to claude3haiku")
    
    # Test with variations
    assert cog.has_bypass_keywords("MIXTRAL: help me")
    assert cog.has_bypass_keywords("try with Gemini please")
    
    # Test negative cases
    assert not cog.has_bypass_keywords("hello world")
    assert not cog.has_bypass_keywords("what's the weather")

def test_has_image_attachments(cog, mock_message):
    """Test image attachment detection"""
    # Test with no attachments
    assert not cog.has_image_attachments(mock_message)
    
    # Test with image attachment
    attachment = MagicMock()
    attachment.content_type = "image/jpeg"
    mock_message.attachments = [attachment]
    assert cog.has_image_attachments(mock_message)
    
    # Test with non-image attachment
    attachment.content_type = "text/plain"
    assert not cog.has_image_attachments(mock_message)

def test_should_handle_message(cog, mock_message):
    """Test message handling conditions"""
    # Test bot messages
    mock_message.author.bot = True
    assert not cog.should_handle_message(mock_message)
    
    # Test user messages
    mock_message.author.bot = False
    mock_message.channel.id = 123
    cog.active_channels.add(123)
    assert cog.should_handle_message(mock_message)
    
    # Test bypass keywords
    mock_message.content = "!mixtral help"
    assert not cog.should_handle_message(mock_message)
    
    # Test DM channel
    mock_message.content = "hello"
    mock_message.channel = MagicMock(spec=discord.DMChannel)
    assert cog.should_handle_message(mock_message)

@pytest.mark.asyncio
async def test_determine_route(cog, mock_message):
    """Test route determination"""
    # Mock context_cog
    context_cog = AsyncMock()
    context_cog.get_context_messages.return_value = [
        {
            'id': '123',
            'user_id': 'user1',
            'content': 'Previous message',
            'is_assistant': False
        }
    ]
    cog.context_cog = context_cog

    # Test emergency routing
    mock_message.content = "I'm having a mental health crisis"
    response = MagicMock()
    response['choices'] = [{'message': {'content': 'Hermes'}}]
    cog.api_client.call_openrouter = AsyncMock(return_value=response)
    result = await cog.determine_route(mock_message)
    assert result == "Hermes"

    # Test technical routing
    mock_message.content = "How do I implement a distributed system?"
    response['choices'] = [{'message': {'content': 'Nemotron'}}]
    result = await cog.determine_route(mock_message)
    assert result == "Nemotron"

    # Test roleplay routing
    mock_message.content = "The epic saga of the kingdom continues..."
    response['choices'] = [{'message': {'content': 'Magnum'}}]
    result = await cog.determine_route(mock_message)
    assert result == "Magnum"

@pytest.mark.asyncio
async def test_route_to_cog(cog, mock_message):
    """Test message routing to cogs"""
    # Mock target cog
    target_cog = AsyncMock()
    cog.bot.get_cog.return_value = target_cog
    
    # Test successful routing
    await cog.route_to_cog(mock_message, "Mixtral")
    target_cog.handle_message.assert_called_once_with(mock_message)
    
    # Test invalid model
    await cog.route_to_cog(mock_message, "InvalidModel")
    mock_message.channel.send.assert_not_called()
    
    # Test error handling
    target_cog.handle_message.side_effect = Exception("Test error")
    await cog.route_to_cog(mock_message, "Mixtral")
    mock_message.channel.send.assert_called_once()

@pytest.mark.asyncio
async def test_activation_commands(cog):
    """Test channel activation/deactivation"""
    ctx = MagicMock()
    ctx.channel.id = 123
    
    # Test activation
    await cog.activate(ctx)
    assert 123 in cog.active_channels
    ctx.send.assert_called_once()
    
    # Test deactivation
    await cog.deactivate(ctx)
    assert 123 not in cog.active_channels
    assert ctx.send.call_count == 2

@pytest.mark.asyncio
async def test_message_handling(cog, mock_message):
    """Test full message handling flow"""
    # Mock route determination
    cog.determine_route = AsyncMock(return_value="Mixtral")
    cog.route_to_cog = AsyncMock()
    
    # Test normal message handling
    mock_message.content = "Test message"
    await cog.on_message(mock_message)
    cog.determine_route.assert_called_once()
    cog.route_to_cog.assert_called_once()
    
    # Test command message
    mock_message.content = "!help"
    cog.determine_route.reset_mock()
    cog.route_to_cog.reset_mock()
    await cog.on_message(mock_message)
    cog.determine_route.assert_not_called()
    cog.route_to_cog.assert_not_called()

@pytest.mark.asyncio
async def test_error_handling(cog, mock_message):
    """Test error handling in message processing"""
    # Mock error in route determination
    cog.determine_route = AsyncMock(side_effect=Exception("Test error"))
    
    # Test error handling
    await cog.on_message(mock_message)
    mock_message.channel.send.assert_called_once()
    assert "Error" in mock_message.channel.send.call_args[0][0]

def test_cog_check(cog):
    """Test cog check for guild-only commands"""
    ctx = MagicMock()
    
    # Test with guild context
    ctx.guild = MagicMock()
    assert cog.cog_check(ctx)
    
    # Test without guild context
    ctx.guild = None
    assert not cog.cog_check(ctx)

@pytest.mark.asyncio
async def test_setup(bot):
    """Test cog setup"""
    # Test successful setup
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        cog = await RouterCog.setup(bot)
        assert isinstance(cog, RouterCog)
        bot.add_cog.assert_called_once()

    # Test setup failure
    bot.add_cog.side_effect = Exception("Setup failed")
    with pytest.raises(Exception):
        await RouterCog.setup(bot)
