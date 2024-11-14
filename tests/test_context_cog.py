import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import discord
from cogs.context_cog import ContextCog
import sqlite3
from datetime import datetime

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
        mock_connect.return_value.commit = MagicMock()
        cog = ContextCog(bot)
        return cog

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
        
        # Verify SQL query was executed
        mock_cursor.execute.assert_called_once()
        
        # Verify returned messages
        assert len(messages) == 3
        assert messages[0]['id'] == 'msg1'
        assert messages[1]['content'] == '[SUMMARY] Summary'
        assert messages[2]['is_assistant'] == True

@pytest.mark.asyncio
async def test_add_message_to_context(context_cog, mock_message):
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_connect.return_value.commit = MagicMock()
        
        # Mock the fetch_user method
        user = MagicMock(spec=discord.User)
        user.display_name = "TestUser"
        context_cog.bot.fetch_user.return_value = user
        
        # Test adding a user message
        await context_cog.add_message_to_context(
            mock_message.id,
            str(mock_message.channel.id),
            str(mock_message.guild.id),
            str(mock_message.author.id),
            mock_message.content,
            False
        )
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        mock_connect.return_value.commit.assert_called_once()

@pytest.mark.asyncio
async def test_on_message_handling(context_cog, mock_message):
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        # Test regular message
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        
        # Test bot message (should be ignored)
        mock_message.author.bot = True
        mock_add.reset_mock()
        await context_cog.on_message(mock_message)
        mock_add.assert_not_called()

@pytest.mark.asyncio
async def test_empty_message_handling(context_cog, mock_message):
    # Test empty message
    mock_message.content = ""
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        # Empty messages should still be processed for attachments
        mock_add.assert_called_once()

@pytest.mark.asyncio
async def test_whitespace_message_handling(context_cog, mock_message):
    # Test whitespace-only message
    mock_message.content = "   \n   \t   "
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        # Whitespace messages should still be processed for attachments
        mock_add.assert_called_once()

@pytest.mark.asyncio
async def test_duplicate_message_handling(context_cog, mock_message):
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        # Add message for the first time
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        mock_add.reset_mock()
        
        # Try to add the same message again
        await context_cog.on_message(mock_message)
        # Duplicate messages should still be processed
        mock_add.assert_called_once()

@pytest.mark.asyncio
async def test_username_resolution(context_cog, mock_message):
    # Mock the bot's fetch_user method
    mock_user = MagicMock(spec=discord.User)
    mock_user.display_name = "ResolvedUser"
    context_cog.bot.fetch_user.return_value = mock_user
    
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once()
        
        # Verify the message content includes the username
        assert mock_message.author.display_name in mock_add.call_args[0][4]

@pytest.mark.asyncio
async def test_database_initialization(bot):
    """Test database initialization during setup"""
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_connect.return_value.commit = MagicMock()
        
        # Create context cog
        cog = ContextCog(bot)
        
        # Verify database setup
        mock_cursor.executescript.assert_called_once()
        assert hasattr(cog, 'db_path')
        assert cog.db_path == 'databases/interaction_logs.db'

@pytest.mark.asyncio
async def test_database_error_handling(context_cog, mock_message):
    """Test error handling for database operations"""
    with patch('sqlite3.connect', side_effect=sqlite3.Error("Test error")):
        # Test get_context_messages error handling
        messages = await context_cog.get_context_messages("789")
        assert messages == []
        
        # Test add_message_to_context error handling
        await context_cog.add_message_to_context(
            mock_message.id,
            str(mock_message.channel.id),
            str(mock_message.guild.id),
            str(mock_message.author.id),
            mock_message.content,
            False
        )
        # Should not raise an exception
