import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class Claude3SonnetCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-3-Sonnet",
            nickname="Sonnet",
            trigger_words=['claude3sonnet', 'sonnet', 'claude 3 sonnet'],
            model="anthropic/claude-3.5-sonnet:beta",
            provider="openrouter",
            prompt_file="claude",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Claude-3-Sonnet] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Claude-3-Sonnet] Using provider: {self.provider}")
        logging.debug(f"[Claude-3-Sonnet] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Claude-3-Sonnet"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = Claude3SonnetCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Claude-3-Sonnet] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-3-Sonnet] Failed to register cog: {str(e)}", exc_info=True)
        raise