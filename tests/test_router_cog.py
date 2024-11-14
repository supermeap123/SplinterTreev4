import pytest
from cogs.router_cog import RouterCog
from unittest.mock import AsyncMock, MagicMock, patch
import discord

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.api_client = MagicMock()
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
    return message

def test_cog_initialization(cog):
    assert cog.name == "Router"
    assert cog.nickname == "Router"
    assert cog.model == "openpipe:FreeRouter-v2-235"
    assert cog.provider == "openpipe"
    assert cog.supports_vision == False
    assert isinstance(cog.model_mapping, dict)
    assert len(cog.model_mapping) > 0

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

def test_has_code_blocks(cog):
    # Test with code block
    assert cog.has_code_blocks("Here's some code: ```python\nprint('hello')\n```")
    
    # Test without code block
    assert not cog.has_code_blocks("Regular text message")
    
    # Test with inline code
    assert not cog.has_code_blocks("Here's `inline code`")

def test_is_technical_query(cog):
    # Test technical indicators
    assert cog.is_technical_query("I'm getting an error in my code")
    assert cog.is_technical_query("How do I implement this feature?")
    assert cog.is_technical_query("npm install failing")
    assert cog.is_technical_query("```python\nprint('hello')\n```")
    
    # Test non-technical messages
    assert not cog.is_technical_query("How's the weather today?")
    assert not cog.is_technical_query("Tell me a story")

def test_is_creative_request(cog):
    # Test creative indicators
    assert cog.is_creative_request("Write me a story about dragons")
    assert cog.is_creative_request("Can you generate a blog post?")
    assert cog.is_creative_request("Create a poem about nature")
    
    # Test non-creative messages
    assert not cog.is_creative_request("What's the time?")
    assert not cog.is_creative_request("Fix this bug in my code")

def test_is_analytical_query(cog):
    # Test analytical indicators
    assert cog.is_analytical_query("Analyze this data")
    assert cog.is_analytical_query("What is the difference between X and Y?")
    assert cog.is_analytical_query("Explain how this works")
    
    # Test non-analytical messages
    assert not cog.is_analytical_query("Hello!")
    assert not cog.is_analytical_query("Write a story")

def test_is_personal_query(cog):
    # Test personal indicators
    assert cog.is_personal_query("I'm feeling sad today")
    assert cog.is_personal_query("Should I take this job offer?")
    assert cog.is_personal_query("Need advice about my relationship 😢")
    
    # Test non-personal messages
    assert not cog.is_personal_query("What's the weather?")
    assert not cog.is_personal_query("Fix this code")

@pytest.mark.asyncio
async def test_determine_route_vision(cog, mock_message):
    # Test complex vision query
    attachment = MagicMock()
    attachment.content_type = "image/jpeg"
    mock_message.attachments = [attachment]
    mock_message.content = "Can you analyze this complex image and explain what's happening in detail?"
    assert await cog.determine_route(mock_message) == 'Llama32_90b'
    
    # Test simple vision query
    mock_message.content = "What's in this image?"
    assert await cog.determine_route(mock_message) == 'Llama32_11b'

@pytest.mark.asyncio
async def test_determine_route_technical(cog, mock_message):
    # Test complex technical query
    mock_message.content = "```python\ndef complex_function():\n    pass\n```\nCan you help fix this?"
    assert await cog.determine_route(mock_message) == 'Goliath'
    
    # Test error query
    mock_message.content = "I'm getting this error in my code"
    assert await cog.determine_route(mock_message) == 'Nemotron'
    
    # Test how-to query
    mock_message.content = "How do I implement authentication?"
    assert await cog.determine_route(mock_message) == 'Noromaid'

@pytest.mark.asyncio
async def test_determine_route_creative(cog, mock_message):
    # Test poem request
    mock_message.content = "Write a haiku about spring"
    assert await cog.determine_route(mock_message) == 'Claude3Haiku'
    
    # Test article request
    mock_message.content = "Generate a blog post about AI"
    assert await cog.determine_route(mock_message) == 'Pixtral'
    
    # Test long creative request
    mock_message.content = "Write a detailed story about " + "very long content " * 20
    assert await cog.determine_route(mock_message) == 'Magnum'

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
async def test_handle_message(cog, mock_message):
    # Setup mocks
    cog.determine_route = AsyncMock(return_value='Mixtral')
    cog.route_to_cog = AsyncMock()
    
    # Test inactive channel
    mock_message.channel.id = 999
    await cog.handle_message(mock_message)
    assert not cog.determine_route.called
    assert not cog.route_to_cog.called
    
    # Test active channel
    mock_message.channel.id = 123
    cog.active_channels.add(123)
    await cog.handle_message(mock_message)
    cog.determine_route.assert_called_with(mock_message)
    cog.route_to_cog.assert_called_with(mock_message, 'Mixtral')

@pytest.mark.asyncio
async def test_activate_deactivate(cog):
    ctx = MagicMock()
    ctx.channel.id = 123
    ctx.send = AsyncMock()
    
    # Test activation
    await cog.activate(ctx)
    assert 123 in cog.active_channels
    ctx.send.assert_called_with("RouterCog has been activated in this channel.")
    
    # Test deactivation
    await cog.deactivate(ctx)
    assert 123 not in cog.active_channels
    ctx.send.assert_called_with("RouterCog has been deactivated in this channel.")
