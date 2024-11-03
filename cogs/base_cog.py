import discord
from discord.ext import commands
import sqlite3
import json
import os
import logging
from datetime import datetime
import traceback
import asyncio
import re
from shared.utils import get_token_count, get_message_history
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
        self.api_client = api
        self.raw_prompt = self.load_prompt()
        self.sentence_end = re.compile(r'[.!?]\s+|\n\n+|\n(?=[A-Z])|[.!?](?=["\'])\s+')
        self.context_cog = bot.get_cog('ContextCog')

    def load_prompt(self):
        try:
            with open('prompts/consolidated_prompts.json', 'r') as f:
                prompts = json.load(f)
                name_normalized = ''.join(c.lower() for c in self.name if c.isalnum())
                if name_normalized in prompts["system_prompts"]:
                    logging.info(f"Loaded prompt for {self.name} from consolidated file")
                    return prompts["system_prompts"][name_normalized]
                for key, prompt in prompts["system_prompts"].items():
                    key_normalized = ''.join(c.lower() for c in key if c.isalnum())
                    if name_normalized == key_normalized:
                        logging.info(f"Loaded prompt for {self.name} from consolidated file using normalized key {key}")
                        return prompt
                logging.warning(f"No prompt found for {self.name} in consolidated file")
                return ""
        except Exception as e:
            logging.error(f"Failed to load prompt for {self.name}: {str(e)}")
            return ""

    def format_message_content(self, content, context):
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
        result = cursor.fetchone() is None
        conn.close()
        return result

    def should_respond(self, message_content: str) -> bool:
        if not self.trigger_words:
            return False
        message_lower = message_content.lower()
        for trigger in self.trigger_words:
            if trigger.lower() in message_lower:
                return True
        return False

    def split_into_chunks(self, text: str, max_length: int = 1500) -> list:
        chunks = []
        current_chunk = ""
        segments = self.sentence_end.split(text)
        matches = self.sentence_end.finditer(text)
        separators = [match.group() for match in matches]
        segments = [s + (separators[i] if i < len(separators) else '') for i, s in enumerate(segments)]
        for segment in segments:
            if len(current_chunk) + len(segment) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = segment
            else:
                current_chunk += segment
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    async def handle_message(self, message):
        if not message.guild or not message.channel:
            return
        if not self.is_channel_active(str(message.channel.id), str(message.guild.id)):
            return
        if not self.should_respond(message.content):
            return
        try:
            history = self.get_conversation_history(message.channel.id, message.guild.id)
            settings = self.get_guild_settings(message.guild.id)
            self.store_message(
                message.id,
                message.channel.id,
                message.guild.id,
                message.author.id,
                message.content,
                False  # is_assistant
            )
            response = await self.generate_response(message)
            if response is None:
                return
            if hasattr(response, '__aiter__'):
                full_response = ""
                current_chunk = ""
                sent_message = None
                async for chunk in response:
                    if chunk:
                        current_chunk += chunk
                        full_response += chunk
                        chunks = self.split_into_chunks(current_chunk)
                        if len(chunks) > 1:
                            for i, chunk_text in enumerate(chunks[:-1]):
                                if sent_message is None:
                                    sent_message = await message.channel.send(chunk_text)
                                else:
                                    await message.channel.send(chunk_text)
                            current_chunk = chunks[-1]
                if current_chunk:
                    if sent_message is None:
                        sent_message = await message.channel.send(current_chunk)
                    else:
                        await message.channel.send(current_chunk)
                if sent_message:
                    response_id = sent_message.id
                    response_text = full_response
                    self.store_message(
                        response_id,
                        message.channel.id,
                        message.guild.id,
                        self.bot.user.id,
                        response_text,
                        True  # is_assistant
                    )
                    self.update_conversation_history(
                        message.channel.id,
                        message.guild.id, 
                        message.id,
                        response_id,
                        message.content,
                        response_text
                    )
            else:
                chunks = self.split_into_chunks(response, 2000)
                sent_messages = []
                for i, chunk in enumerate(chunks):
                    sent_message = await message.channel.send(chunk)
                    sent_messages.append(sent_message)
                if sent_messages:
                    response_id = sent_messages[0].id
                    response_text = response
                    self.store_message(
                        response_id,
                        message.channel.id,
                        message.guild.id,
                        self.bot.user.id,
                        response_text,
                        True  # is_assistant
                    )
                    self.update_conversation_history(
                        message.channel.id,
                        message.guild.id, 
                        message.id,
                        response_id,
                        message.content,
                        response_text
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
        if not message_id:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO messages
                (message_id, channel_id, guild_id, user_id, author_id, content, is_assistant, emotion, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (str(message_id), str(channel_id), str(guild_id), str(user_id), str(user_id), content, is_assistant, emotion))
            conn.commit()
        except Exception as e:
            logging.error(f"Failed to store message: {str(e)}")
        finally:
            conn.close()

    def get_guild_settings(self, guild_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
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
        try:
            with open('temperatures.json', 'r') as f:
                temps = json.load(f)
                return temps.get(self.name.lower(), 0.7)
        except:
            return 0.7

    async def generate_response(self, message):
        try:
            tz = ZoneInfo("America/Los_Angeles")
            current_time = datetime.now(tz).strftime("%I:%M %p")
            context = {
                "MODEL_ID": self.name,
                "USERNAME": message.author.display_name,
                "DISCORD_USER_ID": message.author.id,
                "TIME": current_time,
                "TZ": "Pacific Time",
                "SERVER_NAME": message.guild.name if message.guild else "Direct Message",
                "CHANNEL_NAME": message.channel.name if hasattr(message.channel, 'name') else "DM"
            }
            formatted_prompt = self.format_message_content(self.raw_prompt, context)
            messages = [{"role": "system", "content": formatted_prompt}]
            messages.append({"role": "user", "content": message.content})
            temperature = self.get_temperature()
            if self.provider == "openrouter":
                response_stream = await self.api_client.call_openrouter(
                    messages=messages,
                    model=self.model,
                    temperature=temperature,
                    stream=True
                )
            elif self.provider == "openpipe":
                response_stream = await self.api_client.call_openpipe(
                    messages=messages,
                    model=self.model,
                    temperature=temperature,
                    stream=True
                )
            else:
                return None
            return response_stream
        except Exception as e:
            logging.error(f"Error processing message for {self.name}: {str(e)}")
            return None

async def setup(bot):
    await bot.add_cog(BaseCog(bot))
