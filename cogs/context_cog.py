import discord
from discord.ext import commands
from config import CONTEXT_WINDOWS, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional

class ContextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'databases/interaction_logs.db'
        self._setup_database()

    def _setup_database(self):
        """Ensure database and tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load and execute schema if needed
                with open('databases/schema.sql', 'r') as f:
                    conn.executescript(f.read())
        except Exception as e:
            logging.error(f"Failed to setup database: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Capture user messages to add to context"""
        # Ignore messages from bots
        if message.author.bot:
            return

        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id) if message.guild else None
        user_id = str(message.author.id)
        content = message.content
        is_assistant = False
        persona_name = None
        emotion = None

        await self.add_message_to_context(channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Capture edited messages to update context"""
        # Ignore messages from bots
        if after.author.bot:
            return

        channel_id = str(after.channel.id)
        guild_id = str(after.guild.id) if after.guild else None
        user_id = str(after.author.id)
        content = after.content
        is_assistant = False
        persona_name = None
        emotion = None

        # Optionally, you might want to update the existing message in the database
        # For simplicity, we'll treat edits as new messages
        await self.add_message_to_context(channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion)

    async def get_context_messages(self, channel_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation context for a channel"""
        try:
            if limit is None:
                limit = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get recent messages with their context
                cursor.execute("""
                    SELECT 
                        m.timestamp,
                        m.user_id,
                        m.persona_name,
                        m.content,
                        m.is_assistant,
                        m.emotion
                    FROM messages m
                    WHERE m.channel_id = ?
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                """, (channel_id, limit))

                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        'timestamp': row['timestamp'],
                        'user_id': row['user_id'],
                        'persona_name': row['persona_name'],
                        'content': row['content'],
                        'is_assistant': bool(row['is_assistant']),
                        'emotion': row['emotion']
                    })

                return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            logging.error(f"Failed to get context messages: {str(e)}")
            return []

    async def add_message_to_context(self, channel_id: str, guild_id: Optional[str], 
                                     user_id: str, content: str, is_assistant: bool,
                                     persona_name: Optional[str] = None, 
                                     emotion: Optional[str] = None) -> bool:
        """Add a new message to the conversation context"""
        try:
            timestamp = datetime.now().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (
                        channel_id, guild_id, user_id, persona_name, 
                        content, is_assistant, emotion, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (channel_id, guild_id, user_id, persona_name, 
                      content, is_assistant, emotion, timestamp))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to add message to context: {str(e)}")
            return False

    async def get_shared_context(self, channel_id: str, user_id: str, 
                                 lookback_hours: int = 24) -> List[Dict]:
        """Get shared context across all agents for a user in a channel"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get recent interactions across all agents
                lookback_time = (datetime.now() - timedelta(hours=lookback_hours)).isoformat()
                cursor.execute("""
                    SELECT 
                        m.timestamp,
                        m.user_id,
                        m.persona_name,
                        m.content,
                        m.is_assistant,
                        m.emotion
                    FROM messages m
                    WHERE m.channel_id = ?
                    AND m.timestamp > ?
                    AND (m.user_id = ? OR m.is_assistant = 1)
                    ORDER BY m.timestamp DESC
                """, (channel_id, lookback_time, user_id))

                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        'timestamp': row['timestamp'],
                        'user_id': row['user_id'],
                        'persona_name': row['persona_name'],
                        'content': row['content'],
                        'is_assistant': bool(row['is_assistant']),
                        'emotion': row['emotion']
                    })

                return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            logging.error(f"Failed to get shared context: {str(e)}")
            return []

    @commands.command(name='setcontext')
    @commands.has_permissions(manage_messages=True)
    async def set_context_window(self, ctx, size: int):
        """Set the context window size for the current channel"""
        if size < 1 or size > MAX_CONTEXT_WINDOW:
            await ctx.reply(f"❌ Context window size must be between 1 and {MAX_CONTEXT_WINDOW}")
            return

        channel_id = str(ctx.channel.id)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO context_windows (channel_id, window_size)
                    VALUES (?, ?)
                """, (channel_id, size))
                conn.commit()

                # Update in-memory cache
                CONTEXT_WINDOWS[channel_id] = size

                await ctx.reply(f"✅ Context window size for this channel set to {size} messages")
        except Exception as e:
            logging.error(f"Failed to set context window: {str(e)}")
            await ctx.reply("❌ Failed to set context window size")

    @commands.command(name='getcontext')
    async def get_context_window(self, ctx):
        """Get the current context window size for this channel"""
        channel_id = str(ctx.channel.id)
        try:
            size = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
            await ctx.reply(f"📝 Current context window size: {size} messages")
        except Exception as e:
            logging.error(f"Failed to get context window: {str(e)}")
            await ctx.reply(f"📝 Current context window size: {DEFAULT_CONTEXT_WINDOW} messages (default)")

    @commands.command(name='resetcontext')
    @commands.has_permissions(manage_messages=True)
    async def reset_context_window(self, ctx):
        """Reset the context window size to default for this channel"""
        channel_id = str(ctx.channel.id)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM context_windows
                    WHERE channel_id = ?
                """, (channel_id,))
                conn.commit()

                # Update in-memory cache
                if channel_id in CONTEXT_WINDOWS:
                    del CONTEXT_WINDOWS[channel_id]

                await ctx.reply(f"✅ Context window size reset to default ({DEFAULT_CONTEXT_WINDOW} messages)")
        except Exception as e:
            logging.error(f"Failed to reset context window: {str(e)}")
            await ctx.reply("❌ Failed to reset context window size")

    @commands.command(name='clearcontext')
    @commands.has_permissions(manage_messages=True)
    async def clear_context(self, ctx, hours: Optional[int] = 24):
        """Clear conversation context for this channel"""
        channel_id = str(ctx.channel.id)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if hours:
                    # Clear messages older than specified hours
                    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                    cursor.execute("""
                        DELETE FROM messages
                        WHERE channel_id = ? AND timestamp < ?
                    """, (channel_id, cutoff_time))
                else:
                    # Clear all messages
                    cursor.execute("""
                        DELETE FROM messages
                        WHERE channel_id = ?
                    """, (channel_id,))
                conn.commit()

                await ctx.reply(f"🗑️ Cleared conversation context{f' older than {hours} hours' if hours else ''}")
        except Exception as e:
            logging.error(f"Failed to clear context: {str(e)}")
            await ctx.reply("❌ Failed to clear conversation context")

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
