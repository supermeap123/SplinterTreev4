import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class GeminiProCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemini-Pro",
            nickname="GeminiPro",
            trigger_words=['geminipro', 'gemini pro'],
            model="google/gemini-pro-1.5",
            provider="openrouter",
            prompt_file="gemini",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Gemini-Pro] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Gemini-Pro] Using provider: {self.provider}")
        logging.debug(f"[Gemini-Pro] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Gemini-Pro"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = GeminiProCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Gemini-Pro] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Gemini-Pro] Failed to register cog: {str(e)}", exc_info=True)
        raise