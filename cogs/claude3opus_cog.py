import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class Claude3OpusCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-3-Opus",  # Matches name in temperatures.json
            nickname="Opus",  # Changed to be more specific
            trigger_words=['opus', 'claude3opus', 'claude 3 opus'],  # Removed overlapping triggers
            model="anthropic/claude-3-opus:beta",
            provider="openrouter",
            prompt_file="claude3opus",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[{self.name}] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[{self.name}] Using provider: {self.provider}")
        logging.debug(f"[{self.name}] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return self.name

    # Removed redundant on_message handler - using base_cog's handle_message

async def setup(bot):
    try:
        cog = Claude3OpusCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-3-Opus] Failed to register cog: {str(e)}", exc_info=True)
        raise
