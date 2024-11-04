import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class GeminiCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemini",
            nickname="Gemini",
            trigger_words=['gemini'],
            model="google/gemini-pro-1.5",
            provider="openrouter",
            prompt_file="gemini",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Gemini] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Gemini] Using provider: {self.provider}")
        logging.debug(f"[Gemini] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Gemini"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = GeminiCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Gemini] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Gemini] Failed to register cog: {str(e)}", exc_info=True)
        raise