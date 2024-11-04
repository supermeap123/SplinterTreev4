import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class RPlusCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="R-Plus",
            nickname="RPlus",
            trigger_words=['rplus', 'r plus'],
            model="cohere/command-r-plus",
            provider="openrouter",
            prompt_file="rplus",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[R-Plus] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[R-Plus] Using provider: {self.provider}")
        logging.debug(f"[R-Plus] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "R-Plus"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = RPlusCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[R-Plus] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[R-Plus] Failed to register cog: {str(e)}", exc_info=True)
        raise