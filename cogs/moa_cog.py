import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class MOACog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="MOA",
            nickname="MOA",
            trigger_words=['moa'],
            model="openpipe:moa-gpt-4o-v1",
            provider="openpipe",
            prompt_file="None",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[MOA] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[MOA] Using provider: {self.provider}")
        logging.debug(f"[MOA] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "MOA"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = MOACog(bot)
        await bot.add_cog(cog)
        logging.info(f"[MOA] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[MOA] Failed to register cog: {str(e)}", exc_info=True)
        raise