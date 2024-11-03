import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class Claude3OpusCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot,
                         name="Claude-3-Opus",
                         nickname="Claude 3 Opus",
                         trigger_words=["claude3opus", "claude 3 opus", "claude3_opus", "claude 3_opus"],
                         model="anthropic/claude-3-opus:beta",
                         provider="openrouter")

    async def handle_message(self, message):
        await super().handle_message(message)


async def setup(bot):
    cog = Claude3OpusCog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
