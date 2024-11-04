import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class NemotronCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Nemotron",
            nickname="Nemotron",
            trigger_words=['nemotron'],
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            provider="openrouter",
            prompt_file="nemotron",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Nemotron] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Nemotron] Using provider: {self.provider}")
        logging.debug(f"[Nemotron] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Nemotron"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = NemotronCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Nemotron] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Nemotron] Failed to register cog: {str(e)}", exc_info=True)
        raise