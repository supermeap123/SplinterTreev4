import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion
import json
import time

class SydneyCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Sydney",
            nickname="Sydney", 
            trigger_words=['sydney', 'syd', 'mama kunty'],
            model="openpipe:Sydney-Court",
            provider="openpipe",
            prompt_file="sydney_prompts",
            supports_vision=True
        )
        logging.debug(f"[Sydney] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Sydney] Using provider: {self.provider}")
        logging.debug(f"[Sydney] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Sydney] Failed to load temperatures.json: {str(e)}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Sydney"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def generate_response(self, message):
        """Generate a response using OpenPipe"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(channel_id, limit=50)
            
            # Format history messages with proper roles
            for msg in history_messages:
                role = "assistant" if msg['is_assistant'] else "user"
                content = msg['content']
                
                # Handle system summaries
                if msg['user_id'] == 'SYSTEM' and content.startswith('[SUMMARY]'):
                    role = "system"
                    content = content[9:].strip()  # Remove [SUMMARY] prefix
                
                messages.append({
                    "role": role,
                    "content": content
                })

            # Add current message with any image descriptions
            if message.attachments:
                # Get alt text for this message
                alt_text = await self.context_cog.get_alt_text(str(message.id))
                if alt_text:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message.content},
                            {"type": "text", "text": f"Image description: {alt_text}"}
                        ]
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": message.content
                    })
            else:
                messages.append({
                    "role": "user",
                    "content": message.content
                })

            logging.debug(f"[Sydney] Sending {len(messages)} messages to API")
            logging.debug(f"[Sydney] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Sydney] Using temperature: {temperature}")

            # Call OpenPipe API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for Sydney: {str(e)}")
            return None

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = SydneyCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Sydney] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Sydney] Failed to register cog: {str(e)}", exc_info=True)
        raise
