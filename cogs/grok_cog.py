import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class GrokCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Grok",
            nickname="Grok",
            trigger_words=['grok'],
            model="x-ai/grok-beta",
            provider="openrouter",
            prompt_file="grok",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Grok] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Grok] Using provider: {self.provider}")
        logging.debug(f"[Grok] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Grok"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = GrokCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Grok] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Grok] Failed to register cog: {str(e)}", exc_info=True)
        raise