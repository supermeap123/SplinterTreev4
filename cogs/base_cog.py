import discord
from discord.ext import commands
import sqlite3
import json
import os
from datetime import datetime
import traceback
import asyncio
from shared.utils import get_token_count

class BaseCog(commands.Cog):
    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.db_path = 'databases/bot.db'
        self.ensure_database()
        
        # Store additional parameters
        self.name = kwargs.get('name', "base")
        self.nickname = kwargs.get('nickname', self.name)
        self.trigger_words = kwargs.get('trigger_words', [])
        self.model = kwargs.get('model', "base")
        self.provider = kwargs.get('provider', None)
        self.prompt_file = kwargs.get('prompt_file', None)
        self.supports_vision = kwargs.get('supports_vision', False)
        self.max_tokens = kwargs.get('max_tokens', 4096)
        
        # Load prompt from file if specified
        self.raw_prompt = self.load_prompt()
        
    def load_prompt(self):
        """Load prompt from the specified prompt file"""
        if not self.prompt_file:
            return ""
            
        try:
            with open(f"prompts/{self.prompt_file}.json", 'r') as f:
                prompts = json.load(f)
                # Convert name to lowercase and remove non-alphanumeric chars for matching
                key = ''.join(c.lower() for c in self.name if c.isalnum())
                # Special case for Sydney which uses sydney_prompts as key
                if key == "sydney":
                    key = "sydney_prompts"
                return prompts["system_prompts"].get(key, "")
        except Exception as e:
            logging.error(f"Failed to load prompt for {self.name}: {str(e)}")
            return ""
            
    def format_message_content(self, content, context):
        """Format message content with context variables"""
        try:
            return content.format(**context)
        except Exception as e:
            logging.error(f"Failed to format message content: {str(e)}")
            return content
        
    def ensure_database(self):
        os.makedirs('databases', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        with open('databases/schema.sql', 'r') as schema_file:
            cursor.executescript(schema_file.read())
        
        conn.commit()
        conn.close()

    def is_channel_active(self, channel_id: str, guild_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 1 FROM deactivated_channels 
            WHERE channel_id = ? AND guild_id = ?
        ''', (channel_id, guild_id))

        result = cursor.fetchone() is None  # Channel is active if it's not in deactivated_channels
        conn.close()
        return result

    async def process_message(self, message):
        if not self.is_channel_active(str(message.channel.id), str(message.guild.id)):
            return

        try:
            # Get conversation history
            history = self.get_conversation_history(message.channel.id, message.guild.id)
            
            # Get guild settings
            settings = self.get_guild_settings(message.guild.id)
            
            # Process message and get response
            response = await self.get_ai_response(message.content, history, settings["temperature"])
            
            # Split response if too long
            if len(response) > 2000:
                # Split into chunks of 2000 chars
                chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
                sent_messages = []
                for chunk in chunks:
                    sent_message = await message.channel.send(chunk)
                    sent_messages.append(sent_message)
                
                # Use the first sent message ID for history tracking
                response_id = sent_messages[0].id
            else:
                sent_message = await message.channel.send(response)
                response_id = sent_message.id
            
            # Update conversation history
            self.update_conversation_history(
                message.channel.id,
                message.guild.id, 
                message.id,
                response_id,
                message.content,
                response
            )
            
            # Store message in database
            self.store_message(
                message.id,
                message.channel.id,
                message.guild.id,
                message.author.id,
                message.content
            )
            
        except Exception as e:
            print(f"Error in {self.name} cog:")
            traceback.print_exc()
            await message.channel.send(f"Error processing message: {str(e)}")

    def get_conversation_history(self, channel_id, guild_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT last_human, last_assistant
            FROM channels
            WHERE channel_id = ? AND guild_id = ?
        ''', (str(channel_id), str(guild_id)))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "human": result[0],
                "assistant": result[1]
            }
        return None

    def update_conversation_history(self, channel_id, guild_id, message_id, response_id, human, assistant):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO channels 
            (channel_id, guild_id, last_message_id, last_response_id, last_human, last_assistant, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (str(channel_id), str(guild_id), str(message_id), str(response_id), human, assistant))
        
        conn.commit()
        conn.close()

    def store_message(self, message_id, channel_id, guild_id, author_id, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO messages
            (message_id, channel_id, guild_id, author_id, content, timestamp)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (str(message_id), str(channel_id), str(guild_id), str(author_id), content))
        
        conn.commit()
        conn.close()

    def get_guild_settings(self, guild_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get or create guild settings
        cursor.execute('''
            INSERT OR IGNORE INTO guilds (guild_id)
            VALUES (?)
        ''', (str(guild_id),))
        
        cursor.execute('''
            SELECT active_model, temperature
            FROM guilds
            WHERE guild_id = ?
        ''', (str(guild_id),))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            "model": result[0],
            "temperature": result[1]
        }

    def get_temperature(self):
        """Get the temperature setting for this model"""
        try:
            with open('temperatures.json', 'r') as f:
                temps = json.load(f)
                return temps.get(self.name.lower(), 0.7)  # Default to 0.7 if not found
        except:
            return 0.7  # Default if file not found or error

    async def get_ai_response(self, message, history, temperature):
        # Override in subclasses
        raise NotImplementedError

async def setup(bot):
    await bot.add_cog(BaseCog(bot))
