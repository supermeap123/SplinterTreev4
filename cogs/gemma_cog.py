import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class GemmaCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemma",
            nickname="Gemma",
            trigger_words=['gemma'],
            model="google/gemma-2-27b-it",
            provider="openrouter",
            prompt_file="gemma",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Gemma] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Gemma] Using provider: {self.provider}")
        logging.debug(f"[Gemma] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Gemma"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = GemmaCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Gemma] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Gemma] Failed to register cog: {str(e)}", exc_info=True)
        raise