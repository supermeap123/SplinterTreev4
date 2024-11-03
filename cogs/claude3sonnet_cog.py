import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class Claude3SonnetCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot,
                         name="Claude-3.5-Sonnet",
                         nickname="Claude 3.5 Sonnet",
                         trigger_words=["claude35sonnet", "claude 3.5 sonnet", "claude3.5sonnet", "claude 3.5sonnet"],
                         model="anthropic/claude-3.5-sonnet:beta",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        # Let base_cog handle message processing
        await super().handle_message(message)


async def setup(bot):
    cog = Claude3SonnetCog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
