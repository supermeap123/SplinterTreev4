import discord
from discord.ext import commands
import sqlite3
import json
import os
import logging
from datetime import datetime
import traceback
import asyncio
from shared.utils import get_token_count
from shared.api import api

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
        
        # Initialize API client
        self.api_client = api
        
        # Load prompt from consolidated file
        self.raw_prompt = self.load_prompt()
        
    def load_prompt(self):
        """Load prompt from the consolidated prompts file"""
        try:
            with open('prompts/consolidated_prompts.json', 'r') as f:
                prompts = json.load(f)
                
                # Try exact match first
                if self.name in prompts["system_prompts"]:
                    logging.info(f"Loaded prompt for {self.name} from consolidated file")
                    return prompts["system_prompts"][self.name]
                
                # Try case-insensitive match
                name_lower = self.name.lower()
                name_normalized = ''.join(c.lower() for c in self.name if c.isalnum())
                
                for key, prompt in prompts["system_prompts"].items():
                    key_lower = key.lower()
                    key_normalized = ''.join(c.lower() for c in key if c.isalnum())
                    
                    if name_lower == key_lower or name_normalized == key_normalized:
                        logging.info(f"Loaded prompt for {self.name} from consolidated file using normalized key {key}")
                        return prompt
                
                logging.warning(f"No prompt found for {self.name} in consolidated file")
                return ""
                
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

    async def handle_message(self, message):
        """Handle incoming messages"""
        if not self.is_channel_active(str(message.channel.id), str(message.guild.id)):
            return

        try:
            # Get conversation history
            history = self.get_conversation_history(message.channel.id, message.guild.id)
            
            # Get guild settings
            settings = self.get_guild_settings(message.guild.id)
            
            # Process message and get response
            response = await self.generate_response(message)
            
            if response is None:
                return
            
            # Handle streaming responses (async generators)
            if hasattr(response, '__aiter__'):
                full_response = ""
                current_chunk = ""
                
                async for chunk in response:
                    if chunk:
                        current_chunk += chunk
                        full_response += chunk
                        
                        # Send chunk when it reaches a reasonable size or contains sentence endings
                        if len(current_chunk) > 1500 or any(end in current_chunk for end in ['. ', '! ', '? ', '\n']):
                            await message.channel.send(current_chunk)
                            current_chunk = ""
                
                # Send any remaining text
                if current_chunk:
                    await message.channel.send(current_chunk)
                
                # Use the first sent message for history tracking
                response_id = message.channel.last_message_id
                response_text = full_response
                
            else:
                # Handle regular string responses
                if len(response) > 2000:
                    # Split into chunks of 2000 chars
                    chunks = [response[i:i + 2000] for i in range(0, len(response), 2000)]
                    sent_messages = []
                    for chunk in chunks:
                        sent_message = await message.channel.send(chunk)
                        sent_messages.append(sent_message)
                    
                    # Use the first sent message ID for history tracking
                    response_id = sent_messages[0].id
                    response_text = response
                else:
                    sent_message = await message.channel.send(response)
                    response_id = sent_message.id
                    response_text = response
            
            # Update conversation history
            self.update_conversation_history(
                message.channel.id,
                message.guild.id, 
                message.id,
                response_id,
                message.content,
                response_text
            )
            
            # Store message in database
            self.store_message(
                message.id,
                message.channel.id,
                message.guild.id,
                message.author.id,
                message.content,
                False  # is_assistant
            )
            
            # Store bot's response in database
            self.store_message(
                response_id,
                message.channel.id,
                message.guild.id,
                self.bot.user.id,
                response_text,
                True  # is_assistant
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

    def store_message(self, message_id, channel_id, guild_id, user_id, content, is_assistant=False, emotion=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO messages
            (message_id, channel_id, guild_id, user_id, author_id, content, is_assistant, emotion, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (str(message_id), str(channel_id), str(guild_id), str(user_id), str(user_id), content, is_assistant, emotion))
        
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

    async def generate_response(self, message):
        """Generate a response to a message. Override this in subclasses."""
        raise NotImplementedError("Subclasses must implement generate_response")

async def setup(bot):
    await bot.add_cog(BaseCog(bot))
