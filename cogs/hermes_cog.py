import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class HermesCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Hermes",
            nickname="Hermes",
            trigger_words=['hermes'],
            model="nousresearch/hermes-3-llama-3.1-405b",
            provider="openrouter",
            prompt_file="hermes",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Hermes] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Hermes] Using provider: {self.provider}")
        logging.debug(f"[Hermes] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Hermes"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = HermesCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Hermes] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Hermes] Failed to register cog: {str(e)}", exc_info=True)
        raise