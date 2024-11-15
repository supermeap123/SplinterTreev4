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
        # Track which channels have had their history loaded
        self.loaded_channels = set()
        # Track message parts for handling split messages
        self.message_parts = {}  # Format: {channel_id: {'message_id': [parts]}}

    def _setup_database(self):
        """Initialize the SQLite database for interaction logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Read and execute schema.sql
                with open('databases/schema.sql', 'r') as f:
                    schema = f.read()
                    cursor.executescript(schema)
                
                conn.commit()
                logging.info("Database setup completed successfully")
        except Exception as e:
            logging.error(f"Failed to set up database: {str(e)}")

    async def _load_channel_history(self, channel_id: str):
        """Load the last 100 messages from a Discord channel into the context database"""
        try:
            if channel_id in self.loaded_channels:
                return

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logging.error(f"Could not find channel {channel_id}")
                return

            messages = []
            async for message in channel.history(limit=100, oldest_first=True):
                if not message.content.startswith('!'):  # Skip commands
                    messages.append(message)

            # Add messages to context in chronological order
            for message in messages:
                guild_id = str(message.guild.id) if message.guild else None
                await self.add_message_to_context(
                    message.id,
                    str(message.channel.id),
                    guild_id,
                    str(message.author.id),
                    message.content,
                    message.author.bot,  # is_assistant
                    None,  # persona_name
                    None   # emotion
                )

            self.loaded_channels.add(channel_id)
            logging.info(f"Loaded history for channel {channel_id}")
        except Exception as e:
            logging.error(f"Failed to load channel history: {str(e)}")

    async def get_context_messages(self, channel_id: str, limit: int = None, exclude_message_id: str = None) -> List[Dict]:
        """Get previous messages from the context database for all users and cogs in the channel"""
        try:
            # Ensure channel history is loaded
            await self._load_channel_history(channel_id)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Increased window size to 100 messages for better context
                window_size = 100
                if limit is not None:
                    window_size = min(window_size, limit)
                
                # Query to get messages from all users and cogs, getting most recent first
                query = '''
                SELECT 
                    m.discord_message_id,
                    m.user_id,
                    m.content,
                    m.is_assistant,
                    m.persona_name,
                    m.emotion,
                    m.timestamp
                FROM messages m
                WHERE m.channel_id = ?
                AND (? IS NULL OR m.discord_message_id != ?)
                AND m.content IS NOT NULL
                AND m.content != ''
                ORDER BY m.timestamp DESC
                LIMIT ?
                '''
                
                cursor.execute(query, (
                    channel_id,
                    exclude_message_id,
                    exclude_message_id,
                    window_size
                ))
                
                messages = []
                seen_contents = set()  # Track seen message contents
                
                for row in cursor.fetchall():
                    content = row[2]
                    
                    # Skip empty or None content
                    if not content or content.isspace():
                        continue
                        
                    # Only skip exact duplicates, removed similarity check
                    if content in seen_contents:
                        continue
                    
                    seen_contents.add(content)
                    messages.append({
                        'id': row[0],  # discord_message_id
                        'user_id': row[1],
                        'content': content,
                        'is_assistant': bool(row[3]),
                        'persona_name': row[4],
                        'emotion': row[5],
                        'timestamp': row[6]
                    })
                
                # Reverse the list to maintain chronological order
                messages.reverse()
                return messages
                
        except Exception as e:
            logging.error(f"Failed to get context messages: {str(e)}")
            return []

    async def add_message_to_context(self, message_id, channel_id, guild_id, user_id, content, is_assistant, persona_name=None, emotion=None):
        """Add a message to the interaction logs"""
        try:
            # Skip empty or whitespace-only content
            if not content or content.isspace():
                return

            # Handle split messages
            if channel_id not in self.message_parts:
                self.message_parts[channel_id] = {}
            
            # If this is a continuation of a split message
            if is_assistant and content.startswith('[') and ']' in content:
                model_name = content[1:content.index(']')]
                actual_content = content[content.index(']')+1:].strip()
                
                # Check if we have previous parts for this message
                for msg_id, parts in self.message_parts[channel_id].items():
                    if parts['model'] == model_name and (datetime.now() - parts['last_update']).seconds < 5:
                        # Append this part
                        parts['content'] += actual_content
                        parts['last_update'] = datetime.now()
                        return  # Don't add to database yet
                
                # If no existing message found, start a new one
                self.message_parts[channel_id][message_id] = {
                    'model': model_name,
                    'content': actual_content,
                    'last_update': datetime.now()
                }
                return  # Don't add to database yet

            # Get username for the message
            if is_assistant:
                # For bot messages, content already has [ModelName] prefix
                prefixed_content = content
            else:
                # For user messages, get the username
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username = user.display_name
                    prefixed_content = f"{username}: {content}"
                except:
                    # If we can't get the username, just use the content as-is
                    prefixed_content = content

            # Clean up old message parts
            current_time = datetime.now()
            for channel in list(self.message_parts.keys()):
                for msg_id in list(self.message_parts[channel].keys()):
                    if (current_time - self.message_parts[channel][msg_id]['last_update']).seconds >= 5:
                        # Add completed message to database
                        completed_content = f"[{self.message_parts[channel][msg_id]['model']}] {self.message_parts[channel][msg_id]['content']}"
                        await self._add_to_database(msg_id, channel, guild_id, user_id, completed_content, is_assistant, persona_name, emotion)
                        del self.message_parts[channel][msg_id]

            # Add regular message to database
            await self._add_to_database(message_id, channel_id, guild_id, user_id, prefixed_content, is_assistant, persona_name, emotion)

        except Exception as e:
            logging.error(f"Failed to add message to context: {str(e)}")

    async def _add_to_database(self, message_id, channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion):
        """Helper method to add a message to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if this message already exists
                cursor.execute('''
                SELECT content FROM messages WHERE discord_message_id = ?
                ''', (str(message_id),))
                
                existing = cursor.fetchone()
                if existing:
                    # Update existing message if content is different
                    if existing[0] != content:
                        cursor.execute('''
                        UPDATE messages 
                        SET content = ?
                        WHERE discord_message_id = ?
                        ''', (content, str(message_id)))
                else:
                    # Insert new message
                    cursor.execute('''
                    INSERT INTO messages 
                    (discord_message_id, channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion, timestamp)
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

            logging.debug(f"Added/updated message in context: {message_id} in channel {channel_id}")
        except Exception as e:
            logging.error(f"Failed to add message to database: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and add them to context"""
        try:
            # Skip command messages and messages from the bot itself
            if message.content.startswith('!') or message.author.id == self.bot.user.id:
                return

            # Skip messages that are model responses (starting with [ModelName])
            if message.content.startswith('[') and ']' in message.content:
                return

            # Add message to context with username prefix
            guild_id = str(message.guild.id) if message.guild else None
            await self.add_message_to_context(
                message.id,
                str(message.channel.id),
                guild_id,
                str(message.author.id),
                message.content,  # Original content - username prefix added in add_message_to_context
                message.author.bot,  # is_assistant
                None,   # persona_name
                None    # emotion
            )
        except Exception as e:
            logging.error(f"Error in on_message: {e}")

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
