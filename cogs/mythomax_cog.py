import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class MythomaxCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Mythomax",
            nickname="Mythomax",
            trigger_words=['mythomax'],
            model="gryphe/mythomax-l2-13b",
            provider="openrouter",
            prompt_file="mythomax",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Mythomax] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Mythomax] Using provider: {self.provider}")
        logging.debug(f"[Mythomax] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Mythomax"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = MythomaxCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Mythomax] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Mythomax] Failed to register cog: {str(e)}", exc_info=True)
        raise