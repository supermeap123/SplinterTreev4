import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class NoromaidCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Noromaid",
            nickname="Noromaid",
            trigger_words=['noromaid'],
            model="neversleep/noromaid-20b",
            provider="openrouter",
            prompt_file="noromaid",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Noromaid] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Noromaid] Using provider: {self.provider}")
        logging.debug(f"[Noromaid] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Noromaid"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = NoromaidCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Noromaid] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Noromaid] Failed to register cog: {str(e)}", exc_info=True)
        raise