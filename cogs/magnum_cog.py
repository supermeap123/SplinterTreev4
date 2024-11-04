import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class MagnumCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Magnum",
            nickname="Magnum",
            trigger_words=['magnum'],
            model="anthracite-org/magnum-v4-72b",
            provider="openrouter",
            prompt_file="magnum",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Magnum] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Magnum] Using provider: {self.provider}")
        logging.debug(f"[Magnum] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Magnum"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = MagnumCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Magnum] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Magnum] Failed to register cog: {str(e)}", exc_info=True)
        raise