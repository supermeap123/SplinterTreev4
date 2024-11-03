import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class Claude1_1Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot, 
                         name="Claude-1.1",
                         nickname="Claude 1.1",
                         trigger_words=["claude1.1", "claude 1.1", "claude1_1", "claude 1_1"],
                         model="anthropic/claude-instant-1.1",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        # Let base_cog handle message processing
        await super().handle_message(message)



async def setup(bot):
    cog = Claude1_1Cog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
