import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class MythomaxCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot,
                         name="Mythomax",
                         nickname="Mythomax",
                         trigger_words=["mythomax"],
                         model="gryphe/mythomax-l2-13b",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        # Let base_cog handle message processing
        await super().handle_message(message)


async def setup(bot):
    cog = MythomaxCog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
