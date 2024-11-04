import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class Claude3OpusCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-3-Opus",
            nickname="Claude",
            trigger_words=['claude3opus', 'opus', 'claude 3 opus'],
            model="anthropic/claude-3-opus:beta",
            provider="openrouter",
            prompt_file="claude",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Claude-3-Opus] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Claude-3-Opus] Using provider: {self.provider}")
        logging.debug(f"[Claude-3-Opus] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Claude-3-Opus"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = Claude3OpusCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Claude-3-Opus] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-3-Opus] Failed to register cog: {str(e)}", exc_info=True)
        raise