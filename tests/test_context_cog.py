import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from discord import Message, User, TextChannel, Guild, DMChannel
from cogs.context_cog import ContextCog
import sqlite3
from datetime import datetime, timedelta

@pytest.fixture
def bot():
    bot = MagicMock()
    bot.fetch_user = AsyncMock()
    return bot

@pytest.fixture
def context_cog(bot):
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        cog = ContextCog(bot)
        return cog

@pytest.fixture
def mock_message():
    message = MagicMock(spec=Message)
    message.author = MagicMock(spec=User)
    message.author.bot = False
    message.author.id = "123"
    message.author.display_name = "TestUser"
    message.content = "Test message"
    message.guild = MagicMock(spec=Guild)
    message.guild.id = "456"
    message.channel = MagicMock(spec=TextChannel)
    message.channel.id = "789"
    message.id = "101112"
    message.created_at = datetime.now()
    return message

def test_initialization(context_cog):
    assert hasattr(context_cog, 'bot')
    assert hasattr(context_cog, 'db_path')
    assert context_cog.db_path == 'databases/interaction_logs.db'

@pytest.mark.asyncio
async def test_get_context_messages(context_cog):
    # Mock database query results
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("msg1", "user1", "Message 1", 0, None, None, "2024-01-01"),
        ("msg2", "SYSTEM", "[SUMMARY] Summary", 0, None, None, "2024-01-01"),
        ("msg3", "user2", "Message 3", 1, "Assistant", "happy", "2024-01-01")
    ]
    
    with patch('sqlite3.connect') as mock_connect:
        mock_connect.return_value.cursor.return_value = mock_cursor
        messages = await context_cog.get_context_messages("789", limit=50)
        
        assert len(messages) == 3
        assert messages[0]['id'] == 'msg1'
        assert messages[1]['content'] == '[SUMMARY] Summary'
        assert messages[2]['is_assistant'] == True

@pytest.mark.asyncio
async def test_add_message_to_context(context_cog, mock_message):
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        # Test adding a user message
        await context_cog.add_message_to_context(
            mock_message.id,
            str(mock_message.channel.id),
            str(mock_message.guild.id),
            str(mock_message.author.id),
            mock_message.content,
            False
        )
        
        # Verify the correct SQL was executed
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'INSERT INTO messages' in call_args[0]
        assert len(call_args[1]) == 8  # Verify all parameters were passed

@pytest.mark.asyncio
async def test_on_message_handling(context_cog, mock_message):
    # Test regular message
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        
        # Verify the correct parameters were passed
        call_args = mock_add.call_args[0]
        assert call_args[0] == mock_message.id
        assert call_args[1] == str(mock_message.channel.id)
        assert call_args[2] == str(mock_message.guild.id)
        assert call_args[3] == str(mock_message.author.id)
        assert call_args[4] == mock_message.content
        assert call_args[5] == False  # is_assistant

@pytest.mark.asyncio
async def test_dm_message_handling(context_cog, mock_message):
    # Test DM message
    mock_message.guild = None
    mock_message.channel = MagicMock(spec=DMChannel)
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        
        # Verify guild_id is None for DMs
        assert mock_add.call_args[0][2] is None

@pytest.mark.asyncio
async def test_bot_message_handling(context_cog, mock_message):
    # Test bot message
    mock_message.author.bot = True
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()

@pytest.mark.asyncio
async def test_command_message_handling(context_cog, mock_message):
    # Test command message (starting with !)
    mock_message.content = "!help"
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_not_called()

@pytest.mark.asyncio
async def test_empty_message_handling(context_cog, mock_message):
    # Test empty message
    mock_message.content = ""
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_not_called()

@pytest.mark.asyncio
async def test_whitespace_message_handling(context_cog, mock_message):
    # Test whitespace-only message
    mock_message.content = "   \n   \t   "
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_not_called()

@pytest.mark.asyncio
async def test_duplicate_message_handling(context_cog, mock_message):
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        # Add message for the first time
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        mock_add.reset_mock()
        
        # Try to add the same message again
        await context_cog.on_message(mock_message)
        mock_add.assert_not_called()

@pytest.mark.asyncio
async def test_username_resolution(context_cog, mock_message):
    # Mock the bot's fetch_user method
    mock_user = MagicMock(spec=User)
    mock_user.display_name = "ResolvedUser"
    context_cog.bot.fetch_user.return_value = mock_user
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        
        # Verify the message content includes the resolved username
        assert "ResolvedUser" in mock_add.call_args[0][4]

@pytest.mark.asyncio
async def test_setup(bot):
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        # Test successful setup
        cog = await ContextCog.setup(bot)
        assert isinstance(cog, ContextCog)
        
        # Verify database initialization
        assert mock_cursor.executescript.called
