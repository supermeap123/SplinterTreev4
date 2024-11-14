import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord import Message, User, TextChannel, Guild
from cogs.context_cog import ContextCog

@pytest.fixture
def context_cog():
    bot = MagicMock()
    return ContextCog(bot)

@pytest.mark.asyncio
@patch('cogs.context_cog.ContextCog.add_message_to_context', new_callable=AsyncMock)
async def test_on_message_includes_bots(mock_add_message, context_cog):
    message = MagicMock(spec=Message)
    message.author.bot = True
    message.content = "Bot message"
    message.guild = MagicMock(spec=Guild)
    message.channel = MagicMock(spec=TextChannel)
    message.id = 123
    message.author.id = 456

    await context_cog.on_message(message)
    mock_add_message.assert_called_once()

@pytest.mark.asyncio
@patch('cogs.context_cog.ContextCog.add_message_to_context', new_callable=AsyncMock)
async def test_on_message_includes_webhooks(mock_add_message, context_cog):
    message = MagicMock(spec=Message)
    message.webhook_id = 789
    message.content = "Webhook message"
    message.guild = MagicMock(spec=Guild)
    message.channel = MagicMock(spec=TextChannel)
    message.id = 123
    message.author.id = 456

    await context_cog.on_message(message)
    mock_add_message.assert_called_once()

@pytest.mark.asyncio
@patch('cogs.context_cog.ContextCog.add_message_to_context', new_callable=AsyncMock)
async def test_on_message_includes_users(mock_add_message, context_cog):
    message = MagicMock(spec=Message)
    message.author.bot = False
    message.content = "User message"
    message.guild = MagicMock(spec=Guild)
    message.channel = MagicMock(spec=TextChannel)
    message.id = 123
    message.author.id = 456

    await context_cog.on_message(message)
    mock_add_message.assert_called_once()
