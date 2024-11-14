import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from discord import Intents
from discord.ext import commands
from bot import SplinterTreeBot, setup_cogs, update_status
from datetime import datetime

class MockState:
    def __init__(self):
        self._command_tree = None

@pytest.mark.asyncio
async def test_cog_loading():
    with patch('discord.ext.commands.Bot.load_extension', new_callable=AsyncMock) as mock_load, \
         patch('discord.ext.commands.Bot._get_state', return_value=MockState()), \
         patch('discord.app_commands.CommandTree'):
        bot = SplinterTreeBot(command_prefix='!', intents=Intents.default())
        bot.cogs_loaded = False
        await setup_cogs(bot)
        assert mock_load.called

@pytest.mark.asyncio
async def test_status_update():
    mock_game = MagicMock(name='game')

    with patch.object(SplinterTreeBot, 'change_presence', new_callable=AsyncMock) as mock_change_presence, \
         patch('discord.Game', return_value=mock_game), \
         patch('bot.get_uptime', return_value='0s'):
        
        bot_instance = SplinterTreeBot(command_prefix='!', intents=Intents.default())
        bot_instance.start_time = datetime.now()
        bot_instance.current_status = None
        bot_instance.get_uptime_enabled = MagicMock(return_value=True)
        
        # Assign the bot instance to the global 'bot' used in update_status
        with patch('bot.bot', bot_instance):
            # Call update_status
            await update_status()
        
            # Verify change_presence was called with the correct game activity
            mock_change_presence.assert_awaited_once_with(activity=mock_game)

@pytest.mark.asyncio
async def test_on_message():
    mock_user = MagicMock()
    mock_user.id = 123
    mock_state = MockState()

    with patch.object(SplinterTreeBot, '_get_state', return_value=mock_state), \
         patch('discord.app_commands.CommandTree'), \
         patch.object(SplinterTreeBot, 'user', new_callable=PropertyMock) as mock_user_prop, \
         patch.object(SplinterTreeBot, 'process_commands', new_callable=AsyncMock) as mock_process_commands:

        mock_user_prop.return_value = mock_user

        bot = SplinterTreeBot(command_prefix='!', intents=Intents.default())

        # Create message mock
        message = MagicMock()
        message.author = MagicMock()
        message.author.id = 456  # Different from bot.user.id
        message.content = "Test message"
        message.attachments = []
        message.reference = None

        await bot.on_message(message)
        mock_process_commands.assert_awaited_once_with(message)

@pytest.mark.asyncio
async def test_on_command_error():
    mock_user = MagicMock()
    mock_user.id = 123
    mock_state = MockState()

    with patch.object(SplinterTreeBot, '_get_state', return_value=mock_state), \
         patch('discord.app_commands.CommandTree'), \
         patch.object(SplinterTreeBot, 'user', new_callable=PropertyMock) as mock_user_prop:

        mock_user_prop.return_value = mock_user

        bot = SplinterTreeBot(command_prefix='!', intents=Intents.default())

        ctx = AsyncMock()
        error = commands.CommandNotFound()

        await bot.on_command_error(ctx, error)
        ctx.reply.assert_not_called()  # CommandNotFound should not trigger a reply
