import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class LiquidCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Liquid",
            nickname="Liquid",
            trigger_words=['liquid'],
            model="liquid/lfm-40b",
            provider="openrouter",
            prompt_file="liquid",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Liquid] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Liquid] Using provider: {self.provider}")
        logging.debug(f"[Liquid] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Liquid"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = LiquidCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Liquid] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Liquid] Failed to register cog: {str(e)}", exc_info=True)
        raise