import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class SydneyCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Sydney",
            nickname="Sydney",
            trigger_words=['sydney', 'sydney ai'],
            model="Sydney-Court",
            provider="openpipe",
            prompt_file="sydney",
            supports_vision=False
        )
        logging.debug(f"[Sydney] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Sydney] Using provider: {self.provider}")
        logging.debug(f"[Sydney] Vision support: {self.supports_vision}")

    async def handle_response(self, response_text, message, referenced_message=None):
        """Override handle_response to add interaction logging"""
        # Call parent class's handle_response first
        emotion = await super().handle_response(response_text, message, referenced_message)

        # Add additional logging
        try:
            log_interaction(
                user_id=message.author.id,
                guild_id=message.guild.id if message.guild else None,
                persona_name=self.name,
                user_message=message.content,
                assistant_reply=response_text,
                emotion=emotion
            )
            logging.debug(f"[Sydney] Logged interaction for user {message.author.id}")
        except Exception as e:
            logging.error(f"Failed to log interaction: {str(e)}")

        return emotion

async def setup(bot):
    await bot.add_cog(SydneyCog(bot))
