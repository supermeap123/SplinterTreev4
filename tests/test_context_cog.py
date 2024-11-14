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
    bot.get_channel = MagicMock()
    return bot

@pytest.fixture
def mock_schema():
    return """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_message_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        guild_id TEXT,
        user_id TEXT NOT NULL,
        content TEXT,
        is_assistant BOOLEAN DEFAULT 0,
        persona_name TEXT,
        emotion TEXT,
        timestamp TEXT NOT NULL
    );
    """

@pytest.fixture
def context_cog(bot, mock_schema):
    with patch('builtins.open', create=True) as mock_open, \
         patch('sqlite3.connect') as mock_connect:
        # Mock schema.sql file read
        mock_open.return_value.__enter__.return_value.read.return_value = mock_schema
        
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value.commit = MagicMock()
        
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

@pytest.fixture
def mock_channel_history():
    """Create mock messages for channel history"""
    messages = []
    for i in range(50):
        msg = MagicMock(spec=discord.Message)
        msg.id = f"msg{i}"
        msg.content = f"Historical message {i}"
        msg.author = MagicMock(spec=discord.Member)
        msg.author.id = f"user{i}"
        msg.author.bot = False if i % 2 == 0 else True
        msg.guild = MagicMock(spec=discord.Guild)
        msg.guild.id = "456"
        messages.append(msg)
    return messages

@pytest.mark.asyncio
async def test_load_channel_history(context_cog, mock_channel_history):
    """Test loading channel history"""
    channel = MagicMock(spec=discord.TextChannel)
    channel.history.return_value.flatten = AsyncMock(return_value=mock_channel_history)
    context_cog.bot.get_channel.return_value = channel

    # Test loading history for a new channel
    await context_cog._load_channel_history("789")
    
    # Verify channel history was fetched
    channel.history.assert_called_once_with(limit=50, oldest_first=True)
    
    # Verify messages were added to context
    assert "789" in context_cog.loaded_channels
    
    # Test loading history for an already loaded channel
    channel.history.reset_mock()
    await context_cog._load_channel_history("789")
    
    # Verify history wasn't fetched again
    channel.history.assert_not_called()

@pytest.mark.asyncio
async def test_get_context_messages(context_cog, mock_channel_history):
    """Test getting context messages with history loading"""
    # Mock database query results
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        ("msg1", "user1", "Message 1", 0, None, None, "2024-01-01"),
        ("msg2", "SYSTEM", "[SUMMARY] Summary", 0, None, None, "2024-01-01"),
        ("msg3", "user2", "Message 3", 1, "Assistant", "happy", "2024-01-01")
    ]
    
    # Mock channel history
    channel = MagicMock(spec=discord.TextChannel)
    channel.history.return_value.flatten = AsyncMock(return_value=mock_channel_history)
    context_cog.bot.get_channel.return_value = channel
    
    with patch('sqlite3.connect') as mock_connect:
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        messages = await context_cog.get_context_messages("789", limit=50)
        
        # Verify channel history was loaded
        assert "789" in context_cog.loaded_channels
        
        # Verify SQL query was executed
        mock_cursor.execute.assert_called()
        
        # Verify returned messages
        assert len(messages) == 3
        assert messages[0]['id'] == 'msg1'
        assert messages[1]['content'] == '[SUMMARY] Summary'
        assert messages[2]['is_assistant'] == True

@pytest.mark.asyncio
async def test_add_message_to_context(context_cog, mock_message):
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No existing message
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
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
        mock_cursor.execute.assert_has_calls([
            # First call to check for existing message
            call('SELECT content FROM messages WHERE discord_message_id = ?', (str(mock_message.id),)),
            # Second call to insert the message
            call('''
                INSERT INTO messages 
                (discord_message_id, channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', 
                (str(mock_message.id), str(mock_message.channel.id), str(mock_message.guild.id), 
                 str(mock_message.author.id), f"TestUser: {mock_message.content}", False, None, None, mock.ANY)
            )
        ])

@pytest.mark.asyncio
async def test_on_message_handling(context_cog, mock_message):
    with patch.object(context_cog, 'add_message_to_context', new_callable=AsyncMock) as mock_add:
        # Test regular message
        await context_cog.on_message(mock_message)
        mock_add.assert_called_once_with(
            mock_message.id,
            str(mock_message.channel.id),
            str(mock_message.guild.id),
            str(mock_message.author.id),
            mock_message.content,
            False,
            None,
            None
        )
        
        # Test command message (should be skipped)
        mock_message.content = "!command"
        mock_add.reset_mock()
        await context_cog.on_message(mock_message)
        mock_add.assert_not_called()

@pytest.mark.asyncio
async def test_username_resolution(context_cog, mock_message):
    # Mock the bot's fetch_user method
    mock_user = MagicMock(spec=discord.User)
    mock_user.display_name = "ResolvedUser"
    context_cog.bot.fetch_user.return_value = mock_user
    
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No existing message
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        # Test adding a message
        await context_cog.add_message_to_context(
            mock_message.id,
            str(mock_message.channel.id),
            str(mock_message.guild.id),
            str(mock_message.author.id),
            mock_message.content,
            False
        )
        
        # Verify the message content includes the resolved username
        insert_call = [call for call in mock_cursor.execute.call_args_list if "INSERT INTO messages" in call[0][0]][0]
        content_param = insert_call[0][1][4]  # Get the content parameter
        assert "ResolvedUser: " in content_param

@pytest.mark.asyncio
async def test_database_initialization(bot, mock_schema):
    """Test database initialization during setup"""
    with patch('builtins.open', create=True) as mock_open, \
         patch('sqlite3.connect') as mock_connect:
        # Mock schema.sql file read
        mock_open.return_value.__enter__.return_value.read.return_value = mock_schema
        
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        # Create context cog
        cog = ContextCog(bot)
        
        # Verify database setup
        mock_cursor.executescript.assert_called_once_with(mock_schema)
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
