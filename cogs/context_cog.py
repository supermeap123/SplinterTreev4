import discord
from discord.ext import commands
from config import CONTEXT_WINDOWS, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW, OPENPIPE_API_KEY, OPENPIPE_API_URL
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
import textwrap
from openai import OpenAI

class ContextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'databases/interaction_logs.db'
        self._setup_database()
        self.summary_chunk_hours = 24  # Summarize every 24 hours of chat
        self.last_summary_check = {}  # Track last summary generation per channel
        self.openai_client = OpenAI(
            base_url=OPENPIPE_API_URL,
            api_key=OPENPIPE_API_KEY
        )
        # Track last message per role to prevent duplicates
        self.last_messages = {}  # Format: {channel_id: {'user': msg, 'assistant': msg}}

    def _setup_database(self):
        """Initialize the SQLite database for interaction logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create messages table if not exists
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    channel_id TEXT,
                    guild_id TEXT,
                    user_id TEXT,
                    content TEXT,
                    is_assistant BOOLEAN,
                    persona_name TEXT,
                    emotion TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create context_windows table if not exists
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS context_windows (
                    channel_id TEXT PRIMARY KEY,
                    window_size INTEGER
                )
                ''')
                
                conn.commit()
                logging.info("Database setup completed successfully")
        except Exception as e:
            logging.error(f"Failed to set up database: {str(e)}")

    async def get_context_messages(self, channel_id: str, limit: int = None, exclude_message_id: str = None) -> List[Dict]:
        """Get previous messages from the context database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get context window size for this channel
                window_size = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
                if limit is not None:
                    window_size = min(window_size, limit)
                
                # Get messages ordered by timestamp, excluding duplicates and specified message
                cursor.execute('''
                WITH RankedMessages AS (
                    SELECT 
                        id, user_id, content, is_assistant, persona_name, emotion, timestamp,
                        LAG(content) OVER (PARTITION BY is_assistant ORDER BY timestamp) as prev_content
                    FROM messages
                    WHERE channel_id = ? AND (? IS NULL OR id != ?)
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
                SELECT id, user_id, content, is_assistant, persona_name, emotion, timestamp
                FROM RankedMessages
                WHERE content != prev_content OR prev_content IS NULL
                ORDER BY timestamp ASC
                ''', (channel_id, exclude_message_id, exclude_message_id, window_size))
                
                messages = []
                seen_contents = set()  # Track seen message contents
                
                for row in cursor.fetchall():
                    content = row[2]
                    # Skip if we've seen this content before
                    if content in seen_contents:
                        continue
                    seen_contents.add(content)
                    
                    messages.append({
                        'id': row[0],
                        'user_id': row[1],
                        'content': content,
                        'is_assistant': bool(row[3]),
                        'persona_name': row[4],
                        'emotion': row[5],
                        'timestamp': row[6]
                    })
                
                return messages
                
        except Exception as e:
            logging.error(f"Failed to get context messages: {str(e)}")
            return []

    async def add_message_to_context(self, message_id, channel_id, guild_id, user_id, content, is_assistant, persona_name=None, emotion=None):
        """Add a message to the interaction logs"""
        try:
            # Check for duplicate content
            last_msg = self.last_messages.get(channel_id, {}).get('assistant' if is_assistant else 'user')
            if last_msg and last_msg['content'] == content:
                logging.debug(f"Skipping duplicate message content in channel {channel_id}")
                return

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if this message already exists
                cursor.execute('''
                SELECT content FROM messages WHERE id = ?
                ''', (str(message_id),))
                
                existing = cursor.fetchone()
                if existing:
                    logging.debug(f"Message {message_id} already exists in context")
                    return
                
                cursor.execute('''
                INSERT OR REPLACE INTO messages 
                (id, channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(message_id), 
                    str(channel_id), 
                    str(guild_id) if guild_id else None, 
                    str(user_id), 
                    content, 
                    is_assistant, 
                    persona_name, 
                    emotion, 
                    datetime.now().isoformat()
                ))
                
                conn.commit()

            # Update last message tracking
            if channel_id not in self.last_messages:
                self.last_messages[channel_id] = {}
            self.last_messages[channel_id]['assistant' if is_assistant else 'user'] = {
                'content': content,
                'timestamp': datetime.now()
            }

            logging.debug(f"Added message to context: {message_id} in channel {channel_id}")
        except Exception as e:
            logging.error(f"Failed to add message to context: {str(e)}")

    @commands.command(name='st_setcontext')
    @commands.has_permissions(manage_messages=True)
    async def st_set_context(self, ctx, size: int):
        """Set the number of previous messages to include in context"""
        try:
            # Validate size
            if size < 1 or size > MAX_CONTEXT_WINDOW:
                await ctx.reply(f"❌ Context size must be between 1 and {MAX_CONTEXT_WINDOW}")
                return

            # Update context window for this channel
            channel_id = str(ctx.channel.id)
            CONTEXT_WINDOWS[channel_id] = size

            # Optionally, save to a persistent configuration file
            try:
                with open('config.py', 'r') as f:
                    config_content = f.read()
                
                # Update or add the CONTEXT_WINDOWS dictionary
                import re
                config_content = re.sub(
                    r'CONTEXT_WINDOWS\s*=\s*{[^}]*}', 
                    f'CONTEXT_WINDOWS = {json.dumps(CONTEXT_WINDOWS)}', 
                    config_content
                )
                
                with open('config.py', 'w') as f:
                    f.write(config_content)
            except Exception as e:
                logging.warning(f"Could not update config.py: {str(e)}")

            await ctx.reply(f"✅ Context window set to {size} messages for this channel")
        except Exception as e:
            logging.error(f"Failed to set context: {str(e)}")
            await ctx.reply("❌ Failed to set context window")

    @commands.command(name='st_getcontext')
    async def st_get_context(self, ctx):
        """View current context window size"""
        try:
            channel_id = str(ctx.channel.id)
            context_size = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
            await ctx.reply(f"📋 Current context window: {context_size} messages")
        except Exception as e:
            logging.error(f"Failed to get context: {str(e)}")
            await ctx.reply("❌ Failed to retrieve context window size")

    @commands.command(name='st_resetcontext')
    @commands.has_permissions(manage_messages=True)
    async def st_reset_context(self, ctx):
        """Reset context window to default size"""
        try:
            channel_id = str(ctx.channel.id)
            
            # Remove channel-specific context setting
            if channel_id in CONTEXT_WINDOWS:
                del CONTEXT_WINDOWS[channel_id]

            # Update config.py
            try:
                with open('config.py', 'r') as f:
                    config_content = f.read()
                
                # Update or add the CONTEXT_WINDOWS dictionary
                import re
                config_content = re.sub(
                    r'CONTEXT_WINDOWS\s*=\s*{[^}]*}', 
                    f'CONTEXT_WINDOWS = {json.dumps(CONTEXT_WINDOWS)}', 
                    config_content
                )
                
                with open('config.py', 'w') as f:
                    f.write(config_content)
            except Exception as e:
                logging.warning(f"Could not update config.py: {str(e)}")

            await ctx.reply(f"🔄 Context window reset to default ({DEFAULT_CONTEXT_WINDOW} messages)")
        except Exception as e:
            logging.error(f"Failed to reset context: {str(e)}")
            await ctx.reply("❌ Failed to reset context window")

    @commands.command(name='st_clearcontext')
    @commands.has_permissions(manage_messages=True)
    async def st_clear_context(self, ctx, hours: Optional[int] = None):
        """Clear conversation history, optionally specify hours"""
        try:
            channel_id = str(ctx.channel.id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if hours:
                    # Delete messages older than specified hours
                    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                    cursor.execute("""
                        DELETE FROM messages
                        WHERE channel_id = ? AND timestamp < ?
                    """, (channel_id, cutoff_time))
                else:
                    # Delete all messages for this channel
                    cursor.execute("""
                        DELETE FROM messages
                        WHERE channel_id = ?
                    """, (channel_id,))
                
                conn.commit()

            # Clear last messages tracking for this channel
            if channel_id in self.last_messages:
                del self.last_messages[channel_id]

            await ctx.reply(f"🗑️ Cleared conversation history{f' older than {hours} hours' if hours else ''}")
        except Exception as e:
            logging.error(f"Failed to clear context: {str(e)}")
            await ctx.reply("❌ Failed to clear conversation history")

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
