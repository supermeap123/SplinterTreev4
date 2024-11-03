import discord
from discord.ext import commands
import logging
from base_cog import BaseCog

class GeminiCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot,
                         name="Gemini",
                         nickname="Gemini",
                         trigger_words=["gemini"],
                         model="google/gemini-pro-1.5",
                         provider="openrouter")
        logging.info(f"[{self.name}] Starting cog setup...")

    async def handle_message(self, message):
        await super().handle_message(message)



async def setup(bot):
    cog = GeminiCog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
