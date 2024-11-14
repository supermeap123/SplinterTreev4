import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from cogs.base_cog import BaseCog, RerollView
import json

class TestCog(BaseCog):
    """Test implementation of BaseCog for testing"""
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="TestModel",
            nickname="Test",
            trigger_words=["test"],
            model="test/model-1",
            provider="test_provider",
            prompt_file="test_prompts",
            supports_vision=False
        )
        # Copy ZALGO_CHARS from parent class
        self.ZALGO_CHARS = BaseCog.ZALGO_CHARS
        self.GLITCH_CHARS = BaseCog.GLITCH_CHARS

    async def _generate_response(self, message):
        async def test_generator():
            yield "Test response"
        return test_generator()

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.get_cog.return_value = MagicMock()
    bot.api_client = MagicMock()
    return bot

@pytest.fixture
def base_cog(bot):
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
            "system_prompts": {
                "test_prompts": "Test prompt for {MODEL_ID} by {USERNAME}"
            }
        })
        return TestCog(bot)

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
    assert base_cog.model == "test/model-1"
    assert base_cog.provider == "test_provider"
    assert base_cog.trigger_words == ["test"]
    assert not base_cog.supports_vision
    assert base_cog.prompt_file == "test_prompts"

def test_generate_glitch_text(base_cog):
    text = "Test"
    glitch_text = base_cog.generate_glitch_text(text)
    assert len(glitch_text) >= len(text)
    cleaned_text = glitch_text
    for char in base_cog.ZALGO_CHARS:
        cleaned_text = cleaned_text.replace(char, '')
    for char in base_cog.GLITCH_CHARS:
        cleaned_text = cleaned_text.replace(char, '')
    assert text in cleaned_text

@pytest.mark.asyncio
async def test_update_bot_profile(base_cog, mock_message):
    guild = mock_message.guild
    guild.me = MagicMock()
    guild.me.edit = AsyncMock()
    
    await base_cog.update_bot_profile(guild, "TestModel")
    
    guild.me.edit.assert_called_once()
    nick = guild.me.edit.call_args[1]['nick']
    assert len(nick) <= 32
    cleaned_nick = nick
    for char in base_cog.ZALGO_CHARS:
        cleaned_nick = cleaned_nick.replace(char, '')
    for char in base_cog.GLITCH_CHARS:
        cleaned_nick = cleaned_nick.replace(char, '')
    assert "TestModel" in cleaned_nick

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
    
    # Verify message was handled
    assert mock_message.id in base_cog.handled_messages

@pytest.mark.asyncio
async def test_format_prompt(base_cog, mock_message):
    formatted_prompt = base_cog.format_prompt(mock_message)
    assert base_cog.name in formatted_prompt
    assert mock_message.author.display_name in formatted_prompt
    assert str(mock_message.author.id) in formatted_prompt
    assert mock_message.guild.name in formatted_prompt
    assert mock_message.channel.name in formatted_prompt

@pytest.mark.asyncio
async def test_reroll_view(base_cog, mock_message):
    # Create RerollView instance
    view = RerollView(base_cog, mock_message, "Original response")
    
    # Mock interaction
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.message = MagicMock()
    interaction.message.edit = AsyncMock()
    
    # Mock button
    button = MagicMock(spec=discord.ui.Button)
    
    # Test successful reroll
    base_cog.generate_response = AsyncMock()
    async def test_generator():
        yield "New response"
    base_cog.generate_response.return_value = test_generator()
    
    # Get the reroll method from the view
    reroll_method = view.reroll.callback
    await reroll_method(view, interaction, button)
    
    # Verify the interaction
    interaction.response.defer.assert_called_once()
    interaction.message.edit.assert_called_once()
    assert "[TestModel]" in interaction.message.edit.call_args[1]['content']

@pytest.mark.asyncio
async def test_error_handling(base_cog, mock_message):
    # Mock channel methods
    mock_message.channel.send = AsyncMock()
    mock_message.channel.typing = AsyncMock()
    
    # Test error in generate_response
    async def error_generator():
        raise Exception("Test error")
    
    base_cog._generate_response = AsyncMock(side_effect=error_generator())
    
    await base_cog.handle_message(mock_message)
    
    # Verify error message was sent
    error_calls = [call for call in mock_message.channel.send.call_args_list if "Error" in call[0][0]]
    assert len(error_calls) > 0
    assert "Test error" in error_calls[-1][0][0]

@pytest.mark.asyncio
async def test_setup(bot):
    """Test cog setup"""
    # Test successful setup
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        cog = await TestCog.setup(bot)
        assert isinstance(cog, TestCog)
        bot.add_cog.assert_called_once()
    
    # Test setup failure
    bot.add_cog.side_effect = Exception("Setup failed")
    with pytest.raises(Exception):
        await TestCog.setup(bot)
