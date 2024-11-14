import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import discord
from discord.ext import commands
from cogs.base_cog import BaseCog, RerollView
import json
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

class TestCog(BaseCog):
    """Test implementation of BaseCog for testing"""
    async def _generate_response(self, message):
        async def test_generator():
            yield "Test response"
        return test_generator()

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.api_client = MagicMock()
    bot.get_cog.return_value = MagicMock()
    bot.user = MagicMock()
    return bot

@pytest.fixture
def base_cog(bot):
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "system_prompts": {
                "test_prompts": "Test prompt for {MODEL_ID}"
            }
        })
        return TestCog(
            bot=bot,
            name="TestModel",
            nickname="Test",
            trigger_words=["test"],
            model="test/model-1",
            provider="test_provider",
            prompt_file="test_prompts",
            supports_vision=False
        )

@pytest.fixture
def mock_message():
    message = MagicMock(spec=discord.Message)
    message.author = MagicMock(spec=discord.Member)
    message.author.bot = False
    message.author.id = "123"
    message.author.display_name = "TestUser"
    message.content = "Test message"
    message.guild = MagicMock(spec=discord.Guild)
    message.guild.name = "Test Server"
    message.guild.id = "456"
    message.channel = MagicMock(spec=discord.TextChannel)
    message.channel.id = "789"
    message.channel.name = "test-channel"
    message.id = "101112"
    return message

def test_initialization(base_cog):
    assert base_cog.name == "TestModel"
    assert base_cog.nickname == "Test"
    assert base_cog.trigger_words == ["test"]
    assert base_cog.model == "test/model-1"
    assert base_cog.provider == "test_provider"
    assert base_cog.prompt_file == "test_prompts"
    assert not base_cog.supports_vision
    assert isinstance(base_cog._image_processing_lock, asyncio.Lock)
    assert isinstance(base_cog.handled_messages, set)

def test_generate_glitch_text(base_cog):
    text = "Test"
    glitch_text = base_cog.generate_glitch_text(text)
    assert len(glitch_text) >= len(text)
    assert text in glitch_text.replace(''.join(base_cog.ZALGO_CHARS), '')

@pytest.mark.asyncio
async def test_update_bot_profile(base_cog, mock_message):
    guild = mock_message.guild
    guild.me = MagicMock()
    guild.me.edit = AsyncMock()
    
    await base_cog.update_bot_profile(guild, "TestModel")
    
    guild.me.edit.assert_called_once()
    nick = guild.me.edit.call_args[1]['nick']
    assert len(nick) <= 32
    assert "TestModel" in nick.replace(''.join(base_cog.ZALGO_CHARS), '')

@pytest.mark.asyncio
async def test_start_typing(base_cog, mock_message):
    mock_message.channel.typing = AsyncMock()
    await base_cog.start_typing(mock_message.channel)
    mock_message.channel.typing.assert_called_once()

def test_is_valid_image_url(base_cog):
    # Test valid image URLs
    assert base_cog.is_valid_image_url("https://example.com/image.jpg")
    assert base_cog.is_valid_image_url("http://test.com/pic.png")
    assert base_cog.is_valid_image_url("https://site.net/photo.jpeg")
    
    # Test invalid URLs
    assert not base_cog.is_valid_image_url("not_a_url")
    assert not base_cog.is_valid_image_url("https://example.com/file.txt")
    assert not base_cog.is_valid_image_url("")

@pytest.mark.asyncio
async def test_handle_message(base_cog, mock_message):
    # Mock context_cog
    context_cog = MagicMock()
    context_cog.add_message_to_context = AsyncMock()
    base_cog.context_cog = context_cog
    
    # Mock channel methods
    mock_message.channel.send = AsyncMock()
    mock_message.channel.typing = AsyncMock()
    mock_message.add_reaction = AsyncMock()
    
    # Test normal message handling
    await base_cog.handle_message(mock_message)
    
    # Verify typing indicator was started
    mock_message.channel.typing.assert_called_once()
    
    # Verify message was added to context
    context_cog.add_message_to_context.assert_called()
    
    # Verify response was sent
    mock_message.channel.send.assert_called()
    
    # Verify message was handled only once
    assert mock_message.id in base_cog.handled_messages

@pytest.mark.asyncio
async def test_format_prompt(base_cog, mock_message):
    formatted_prompt = base_cog.format_prompt(mock_message)
    
    assert base_cog.name in formatted_prompt
    assert mock_message.author.display_name in formatted_prompt
    assert str(mock_message.author.id) in formatted_prompt
    assert mock_message.guild.name in formatted_prompt
    assert mock_message.channel.name in formatted_prompt
    assert "Pacific Time" in formatted_prompt

@pytest.mark.asyncio
async def test_on_message(base_cog, mock_message):
    # Mock handle_message
    base_cog.handle_message = AsyncMock()
    
    # Test bot message (should be ignored)
    mock_message.author.bot = True
    await base_cog.on_message(mock_message)
    base_cog.handle_message.assert_not_called()
    
    # Test message with trigger word
    mock_message.author.bot = False
    mock_message.content = "test the model"
    await base_cog.on_message(mock_message)
    base_cog.handle_message.assert_called_once_with(mock_message)
    
    # Test message without trigger word
    mock_message.content = "regular message"
    base_cog.handle_message.reset_mock()
    await base_cog.on_message(mock_message)
    base_cog.handle_message.assert_not_called()

@pytest.mark.asyncio
async def test_reroll_view(base_cog, mock_message):
    # Create RerollView instance
    view = RerollView(base_cog, mock_message, "Original response")
    
    # Mock interaction
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.message.edit = AsyncMock()
    
    # Mock button
    button = MagicMock(spec=discord.ui.Button)
    
    # Test successful reroll
    base_cog.generate_response = AsyncMock()
    async def test_generator():
        yield "New response"
    base_cog.generate_response.return_value = test_generator()
    
    await view.reroll(interaction, button)
    
    interaction.response.defer.assert_called_once()
    interaction.message.edit.assert_called_once()
    assert "[TestModel]" in interaction.message.edit.call_args[1]['content']
    
    # Test failed reroll
    base_cog.generate_response.return_value = None
    await view.reroll(interaction, button)
    interaction.followup.send.assert_called_with(
        "Failed to generate a new response. Please try again.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_error_handling(base_cog, mock_message):
    # Test error in generate_response
    mock_message.channel.send = AsyncMock()
    base_cog._generate_response = AsyncMock(side_effect=Exception("Test error"))
    
    await base_cog.handle_message(mock_message)
    
    mock_message.channel.send.assert_called_with("❌ Error: Test error")
