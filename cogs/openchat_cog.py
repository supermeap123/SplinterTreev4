import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class OpenChatCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="OpenChat",
            nickname="OpenChat",
            trigger_words=['openchat'],
            model="openchat/openchat-7b",
            provider="openrouter",
            prompt_file="openchat",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[OpenChat] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[OpenChat] Using provider: {self.provider}")
        logging.debug(f"[OpenChat] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "OpenChat"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = OpenChatCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[OpenChat] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[OpenChat] Failed to register cog: {str(e)}", exc_info=True)
        raise