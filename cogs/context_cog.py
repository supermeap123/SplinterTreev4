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
        self.message_parts = {}  # Format: {channel_id: {model_name: {'parts': [], 'last_update': datetime}}}

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

            # Initialize channel in message_parts if not exists
            if channel_id not in self.message_parts:
                self.message_parts[channel_id] = {}

            # Handle streamed assistant messages
            if is_assistant and content.startswith('[') and ']' in content:
                model_name = content[1:content.index(']')]
                actual_content = content[content.index(']')+1:].strip()

                # Initialize or update model's message parts
                if model_name not in self.message_parts[channel_id]:
                    self.message_parts[channel_id][model_name] = {
                        'parts': [],
                        'last_update': datetime.now(),
                        'message_id': message_id
                    }
                
                # Add this part to the message
                self.message_parts[channel_id][model_name]['parts'].append(actual_content)
                self.message_parts[channel_id][model_name]['last_update'] = datetime.now()
                
                # Clean up old message parts and save completed messages
                await self._cleanup_message_parts(channel_id, guild_id, user_id, is_assistant, persona_name, emotion)
                return

            # For non-streamed messages, get username and create prefixed content
            if is_assistant:
                prefixed_content = content
            else:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    username = user.display_name
                    prefixed_content = f"{username}: {content}"
                except:
                    prefixed_content = content

            # Add regular message to database
            await self._add_to_database(message_id, channel_id, guild_id, user_id, prefixed_content, is_assistant, persona_name, emotion)

        except Exception as e:
            logging.error(f"Failed to add message to context: {str(e)}")

    async def _cleanup_message_parts(self, channel_id, guild_id, user_id, is_assistant, persona_name, emotion):
        """Clean up old message parts and save completed messages"""
        current_time = datetime.now()
        for model_name in list(self.message_parts[channel_id].keys()):
            message_data = self.message_parts[channel_id][model_name]
            
            # If it's been more than 2 seconds since the last update, consider the message complete
            if (current_time - message_data['last_update']).seconds >= 2:
                # Combine all parts into the complete message
                complete_content = ''.join(message_data['parts'])
                complete_message = f"[{model_name}] {complete_content}"
                
                # Save the complete message
                await self._add_to_database(
                    message_data['message_id'],
                    channel_id,
                    guild_id,
                    user_id,
                    complete_message,
                    is_assistant,
                    persona_name,
                    emotion
                )
                
                # Remove the completed message from tracking
                del self.message_parts[channel_id][model_name]

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

            # Add message to context with username prefix
            guild_id = str(message.guild.id) if message.guild else None
            await self.add_message_to_context(
                message.id,
                str(message.channel.id),
                guild_id,
                str(message.author.id),
                message.content,
                message.author.bot,  # is_assistant
                None,   # persona_name
                None    # emotion
            )
        except Exception as e:
            logging.error(f"Error in on_message: {e}")

async def setup(bot):
    await bot.add_cog(ContextCog(bot))
