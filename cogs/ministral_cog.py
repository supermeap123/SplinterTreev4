import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class MinistralCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Ministral",
            nickname="Ministral",
            trigger_words=['ministral'],
            model="mistralai/ministral-8b",
            provider="openrouter",
            prompt_file="ministral",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Ministral] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Ministral] Using provider: {self.provider}")
        logging.debug(f"[Ministral] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Ministral"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = MinistralCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Ministral] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Ministral] Failed to register cog: {str(e)}", exc_info=True)
        raise