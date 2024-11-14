import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from cogs.router_cog import RouterCog

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.api_client = MagicMock()
    bot.get_cog.return_value = MagicMock()
    return bot

@pytest.fixture
def mock_message():
    message = MagicMock(spec=discord.Message)
    message.channel = MagicMock(spec=discord.TextChannel)
    message.channel.id = "123"
    message.id = "456"
    message.content = "Test message"
    message.author = MagicMock(spec=discord.Member)
    message.author.bot = False
    message.author.id = "789"
    message.guild = MagicMock(spec=discord.Guild)
    message.guild.id = "101112"
    message.attachments = []
    return message

@pytest.fixture
async def router_cog(mock_bot):
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{"router": 0.5}'
        cog = RouterCog(mock_bot)
        yield cog

@pytest.mark.asyncio
async def test_initialization(router_cog):
    """Test RouterCog initialization"""
    assert router_cog.name == "Router"
    assert router_cog.nickname == "Router"
    assert router_cog.model == "mistralai/ministral-3b"
    assert router_cog.provider == "openrouter"
    assert router_cog.prompt_file == "router"
    assert not router_cog.supports_vision
    assert "UnslopNemo" in router_cog.model_mapping
    assert router_cog.model_mapping["UnslopNemo"] == "UnslopNemoCog"

@pytest.mark.asyncio
async def test_bypass_keywords(router_cog):
    """Test bypass keyword detection"""
    # Test standard model keywords
    assert router_cog.has_bypass_keywords("!mixtral help")
    assert router_cog.has_bypass_keywords("use gemini please")
    assert router_cog.has_bypass_keywords("switch to unslopnemo")
    
    # Test case variations
    assert router_cog.has_bypass_keywords("MIXTRAL: hello")
    assert router_cog.has_bypass_keywords("UnSlopNeMo please")
    
    # Test negative cases
    assert not router_cog.has_bypass_keywords("hello world")
    assert not router_cog.has_bypass_keywords("tell me a story")

@pytest.mark.asyncio
async def test_determine_route_roleplay(router_cog, mock_message):
    """Test routing for roleplay scenarios"""
    context_cog = AsyncMock()
    context_cog.get_context_messages.return_value = []
    router_cog.context_cog = context_cog
    
    # Mock API response
    router_cog.api_client.call_openrouter = AsyncMock()
    
    # Test medium roleplay scenario
    mock_message.content = "The party explores the tavern, looking for information"
    router_cog.api_client.call_openrouter.return_value = {
        "choices": [{"message": {"content": "UnslopNemo"}}]
    }
    result = await router_cog.determine_route(mock_message)
    assert result == "UnslopNemo"
    
    # Test complex roleplay scenario
    mock_message.content = "Clara sits by the fire, reflecting on her journey"
    router_cog.api_client.call_openrouter.return_value = {
        "choices": [{"message": {"content": "Noromaid"}}]
    }
    result = await router_cog.determine_route(mock_message)
    assert result == "Noromaid"

@pytest.mark.asyncio
async def test_determine_route_dm(router_cog, mock_message):
    """Test routing for DM messages"""
    mock_message.channel = MagicMock(spec=discord.DMChannel)
    mock_message.guild = None
    
    context_cog = AsyncMock()
    context_cog.get_context_messages.return_value = []
    router_cog.context_cog = context_cog
    
    router_cog.api_client.call_openrouter = AsyncMock(return_value={
        "choices": [{"message": {"content": "Mixtral"}}]
    })
    
    result = await router_cog.determine_route(mock_message)
    assert result == "Mixtral"
    
    # Verify channel ID handling
    context_cog.get_context_messages.assert_called_with(None, limit=5, exclude_message_id="456")

@pytest.mark.asyncio
async def test_determine_route_error(router_cog, mock_message):
    """Test error handling in route determination"""
    context_cog = AsyncMock()
    context_cog.get_context_messages.side_effect = Exception("Test error")
    router_cog.context_cog = context_cog
    
    result = await router_cog.determine_route(mock_message)
    assert result == "Liquid"  # Should fall back to Liquid on error

@pytest.mark.asyncio
async def test_route_to_cog(router_cog, mock_message):
    """Test message routing to cogs"""
    # Test UnslopNemo routing
    unslopnemo_cog = AsyncMock()
    router_cog.bot.get_cog.return_value = unslopnemo_cog
    
    await router_cog.route_to_cog(mock_message, "UnslopNemo")
    unslopnemo_cog.handle_message.assert_called_once_with(mock_message)
    
    # Test error handling
    unslopnemo_cog.handle_message.side_effect = Exception("Test error")
    mock_message.channel.send = AsyncMock()
    
    await router_cog.route_to_cog(mock_message, "UnslopNemo")
    mock_message.channel.send.assert_called_once()
    assert "Error" in mock_message.channel.send.call_args[0][0]

@pytest.mark.asyncio
async def test_message_handling(router_cog, mock_message):
    """Test full message handling flow"""
    router_cog.determine_route = AsyncMock(return_value="UnslopNemo")
    router_cog.route_to_cog = AsyncMock()
    
    # Test normal message
    await router_cog.on_message(mock_message)
    router_cog.determine_route.assert_called_once()
    router_cog.route_to_cog.assert_called_once_with(mock_message, "UnslopNemo")
    
    # Test bot message (should be ignored)
    mock_message.author.bot = True
    router_cog.determine_route.reset_mock()
    router_cog.route_to_cog.reset_mock()
    
    await router_cog.on_message(mock_message)
    router_cog.determine_route.assert_not_called()
    router_cog.route_to_cog.assert_not_called()

@pytest.mark.asyncio
async def test_channel_activation(router_cog):
    """Test channel activation/deactivation"""
    ctx = MagicMock()
    ctx.channel.id = 123
    ctx.send = AsyncMock()
    
    # Test activation
    await router_cog.activate(ctx)
    assert 123 in router_cog.active_channels
    ctx.send.assert_called_once()
    
    # Test deactivation
    await router_cog.deactivate(ctx)
    assert 123 not in router_cog.active_channels
    assert ctx.send.call_count == 2

@pytest.mark.asyncio
async def test_routing_loop_detection(router_cog):
    """Test routing loop detection"""
    channel_id = 123
    
    # First use
    assert not router_cog.check_routing_loop(channel_id, "UnslopNemo")
    
    # Second use
    assert not router_cog.check_routing_loop(channel_id, "UnslopNemo")
    
    # Third use (should detect loop)
    assert router_cog.check_routing_loop(channel_id, "UnslopNemo")
    
    # Different model (should reset)
    assert not router_cog.check_routing_loop(channel_id, "Mixtral")

@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test cog setup"""
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        
        # Test successful setup
        cog = await RouterCog.setup(mock_bot)
        assert isinstance(cog, RouterCog)
        mock_bot.add_cog.assert_called_once()
        
        # Test setup failure
        mock_bot.add_cog.side_effect = Exception("Setup failed")
        with pytest.raises(Exception):
            await RouterCog.setup(mock_bot)
