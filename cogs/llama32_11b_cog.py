import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class Llama32_11bCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-11b",
            nickname="Llama",
            trigger_words=['llama32', 'llama 32', 'llama'],
            model="meta-llama/llama-3.2-11b-vision-instruct",
            provider="openrouter",
            prompt_file="llama",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Llama-3.2-11b] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Llama-3.2-11b] Using provider: {self.provider}")
        logging.debug(f"[Llama-3.2-11b] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Llama-3.2-11b"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = Llama32_11bCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Llama-3.2-11b] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Llama-3.2-11b] Failed to register cog: {str(e)}", exc_info=True)
        raise