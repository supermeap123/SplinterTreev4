import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion
import time
from datetime import datetime
from zoneinfo import ZoneInfo

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
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Sydney] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Sydney] Using provider: {self.provider}")
        logging.debug(f"[Sydney] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Sydney"

    async def generate_response(self, message):
        """Generate a response using OpenPipe"""
        try:
            # Format context variables
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

            # Format system prompt with variables
            formatted_prompt = self.format_message_content(self.raw_prompt, context)
            messages = [{"role": "system", "content": formatted_prompt}]

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
            logging.debug(f"[Sydney] System prompt: {formatted_prompt}")

            # Get temperature from base_cog
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

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Let base_cog handle message processing
        await super().handle_message(message)

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
