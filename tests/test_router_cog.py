import pytest
from cogs.router_cog import RouterCog
from unittest.mock import AsyncMock, MagicMock, patch
import discord

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.api_client = MagicMock()
    bot.get_cog = MagicMock(return_value=MagicMock(get_context_messages=AsyncMock(return_value=[])))
    bot.user = MagicMock()  # Add bot user for mention checks
    return bot

@pytest.fixture
def cog(mock_bot):
    return RouterCog(mock_bot)

@pytest.fixture
def mock_message():
    message = MagicMock(spec=discord.Message)
    message.content = "Test message"
    message.channel.id = 123
    message.id = 456
    message.author.id = 789
    message.guild.id = 101112
    message.attachments = []
    message.author.bot = False
    message.mentions = []
    return message

def test_cog_initialization(cog):
    assert cog.name == "Router"
    assert cog.nickname == "Router"
    assert cog.model == "mistralai/ministral-3b"
    assert cog.provider == "openrouter"
    assert cog.supports_vision == False
    assert isinstance(cog.model_mapping, dict)
    assert len(cog.model_mapping) > 0
    assert isinstance(cog.bypass_keywords, list)
    assert len(cog.bypass_keywords) > 0
    assert isinstance(cog.model_lookup, dict)
    assert len(cog.model_lookup) > 0

def test_has_bypass_keywords(cog):
    # Test explicit model mentions
    assert cog.has_bypass_keywords("use gemini please")
    assert cog.has_bypass_keywords("switch to mixtral")
    assert cog.has_bypass_keywords("try with claude3haiku")
    
    # Test model names with punctuation
    assert cog.has_bypass_keywords("gemini: help me")
    assert cog.has_bypass_keywords("mixtral, can you help?")
    
    # Test standalone model names
    assert cog.has_bypass_keywords("gemini")
    assert cog.has_bypass_keywords("mixtral")
    
    # Test cases that should not bypass
    assert not cog.has_bypass_keywords("Tell me about artificial intelligence")
    assert not cog.has_bypass_keywords("What's the weather like?")

def test_normalize_model_name(cog):
    # Test exact matches
    assert cog.normalize_model_name("Mixtral") == "Mixtral"
    assert cog.normalize_model_name("Gemini") == "Gemini"
    
    # Test case variations
    assert cog.normalize_model_name("mixtral") == "Mixtral"
    assert cog.normalize_model_name("MIXTRAL") == "Mixtral"
    
    # Test common variations
    assert cog.normalize_model_name("ministral") == "Ministral"
    assert cog.normalize_model_name("ministeral") == "Ministral"
    assert cog.normalize_model_name("mistral") == "Ministral"
    
    # Test unknown models default to Liquid
    assert cog.normalize_model_name("unknown_model") == "Liquid"
    assert cog.normalize_model_name("") == "Liquid"

def test_check_routing_loop(cog):
    channel_id = 123
    
    # First use should not be a loop
    assert not cog.check_routing_loop(channel_id, "Mixtral")
    
    # Second consecutive use should not be a loop
    assert not cog.check_routing_loop(channel_id, "Mixtral")
    
    # Third consecutive use should be a loop
    assert cog.check_routing_loop(channel_id, "Mixtral")
    
    # Different model should reset the counter
    assert not cog.check_routing_loop(channel_id, "Gemini")

def test_has_image_attachments(cog, mock_message):
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
    # Test DM channel
    mock_message.channel = MagicMock(spec=discord.DMChannel)
    assert cog.should_handle_message(mock_message)

    # Test bot mention
    mock_message.channel = MagicMock()  # Reset to regular channel
    mock_message.mentions = [cog.bot.user]
    assert cog.should_handle_message(mock_message)

    # Test activated channel
    mock_message.mentions = []
    mock_message.channel.id = 123
    cog.active_channels.add(123)
    assert cog.should_handle_message(mock_message)

    # Test non-activated channel
    mock_message.channel.id = 456
    assert not cog.should_handle_message(mock_message)

    # Test bot message (should not handle)
    mock_message.author.bot = True
    assert not cog.should_handle_message(mock_message)

    # Test bypass keywords
    mock_message.author.bot = False
    mock_message.content = "use gemini please"
    assert not cog.should_handle_message(mock_message)

@pytest.mark.asyncio
async def test_determine_route_vision(cog, mock_message):
    # Mock OpenRouter API response
    cog.api_client.call_openrouter = AsyncMock()
    
    # Test with image attachment
    attachment = MagicMock()
    attachment.content_type = "image/jpeg"
    mock_message.attachments = [attachment]
    mock_message.content = "Analyze this complex image"
    
    # Mock API to return Llama32_90b for complex image analysis
    cog.api_client.call_openrouter.return_value = {
        'choices': [{'message': {'content': 'Llama32_90b'}}]
    }
    result = await cog.determine_route(mock_message)
    assert result == 'Llama32_90b'
    
    # Test simple image query
    mock_message.content = "What's in this image?"
    cog.api_client.call_openrouter.return_value = {
        'choices': [{'message': {'content': 'Llama32_11b'}}]
    }
    result = await cog.determine_route(mock_message)
    assert result == 'Llama32_11b'

@pytest.mark.asyncio
async def test_determine_route_technical(cog, mock_message):
    cog.api_client.call_openrouter = AsyncMock()
    
    # Test complex technical query
    mock_message.content = "```python\ndef complex_function():\n    pass\n```\nCan you help fix this?"
    cog.api_client.call_openrouter.return_value = {
        'choices': [{'message': {'content': 'Nemotron'}}]
    }
    result = await cog.determine_route(mock_message)
    assert result == 'Nemotron'
    
    # Test error query
    mock_message.content = "I'm getting this error in my code"
    cog.api_client.call_openrouter.return_value = {
        'choices': [{'message': {'content': 'Claude3Haiku'}}]
    }
    result = await cog.determine_route(mock_message)
    assert result == 'Claude3Haiku'

@pytest.mark.asyncio
async def test_determine_route_creative(cog, mock_message):
    cog.api_client.call_openrouter = AsyncMock()
    
    # Test creative writing
    mock_message.content = "Write a story about space exploration"
    cog.api_client.call_openrouter.return_value = {
        'choices': [{'message': {'content': 'Pixtral'}}]
    }
    result = await cog.determine_route(mock_message)
    assert result == 'Pixtral'
    
    # Test current events query
    mock_message.content = "What's the latest news about AI?"
    cog.api_client.call_openrouter.return_value = {
        'choices': [{'message': {'content': 'Sonar'}}]
    }
    result = await cog.determine_route(mock_message)
    assert result == 'Sonar'

@pytest.mark.asyncio
async def test_on_message(cog, mock_message):
    # Setup mocks
    cog.determine_route = AsyncMock(return_value='Mixtral')
    cog.route_to_cog = AsyncMock()
    mock_message.content = "Test message"
    
    # Test bot message (should be ignored)
    mock_message.author.bot = True
    await cog.on_message(mock_message)
    assert not cog.determine_route.called
    assert not cog.route_to_cog.called
    
    # Test regular message in activated channel
    mock_message.author.bot = False
    mock_message.content = "Test message"
    mock_message.channel.id = 123
    cog.active_channels.add(123)
    await cog.on_message(mock_message)
    cog.determine_route.assert_called_with(mock_message)
    cog.route_to_cog.assert_called_with(mock_message, 'Mixtral')
    
    # Test message in non-activated channel
    mock_message.channel.id = 456
    await cog.on_message(mock_message)
    assert len(cog.determine_route.mock_calls) == 1  # No additional calls

@pytest.mark.asyncio
async def test_route_to_cog(cog, mock_message):
    # Setup mock cogs
    test_cog = MagicMock()
    test_cog.handle_message = AsyncMock()
    cog.bot.get_cog.return_value = test_cog
    
    # Test successful routing
    await cog.route_to_cog(mock_message, 'Mixtral')
    cog.bot.get_cog.assert_called_with('MixtralCog')
    test_cog.handle_message.assert_called_with(mock_message)
    
    # Test routing to non-existent cog
    cog.bot.get_cog.return_value = None
    await cog.route_to_cog(mock_message, 'NonExistent')
    # Should log error but not raise exception

@pytest.mark.asyncio
async def test_activate_deactivate(cog):
    # Create mock context
    ctx = MagicMock()
    ctx.channel.id = 123
    ctx.send = AsyncMock()
    ctx.guild = MagicMock()  # Add guild for cog_check
    
    # Get the actual command objects
    activate_command = cog.activate.callback
    deactivate_command = cog.deactivate.callback
    
    # Test activation
    await activate_command(cog, ctx)
    assert 123 in cog.active_channels
    ctx.send.assert_called_with("RouterCog has been activated in this channel. All messages will now be routed to appropriate models.")
    
    # Test deactivation
    await deactivate_command(cog, ctx)
    assert 123 not in cog.active_channels
    ctx.send.assert_called_with("RouterCog has been deactivated in this channel.")
