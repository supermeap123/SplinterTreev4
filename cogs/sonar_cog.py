import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class SonarCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Sonar",
            nickname="Sonar",
            trigger_words=['sonar'],
            model="perplexity/llama-3.1-sonar-huge-128k-online",
            provider="openrouter",
            prompt_file="sonar",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Sonar] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Sonar] Using provider: {self.provider}")
        logging.debug(f"[Sonar] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Sonar"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = SonarCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Sonar] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Sonar] Failed to register cog: {str(e)}", exc_info=True)
        raise