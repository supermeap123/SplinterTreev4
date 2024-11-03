import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class SonarCog(BaseCog, name="Sonar"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @commands.command(name="sonar", aliases=["Sonar"])
    async def sonar_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Sonar")

    async def cog_load(self):
        try:
            await super().cog_load()
            logging.info(f"[Sonar] Registered cog with qualified_name: {self.qualified_name}")
        except Exception as e:
            logging.error(f"[Sonar] Failed to register cog: {str(e)}")
            raise

def setup(bot):
    try:
        bot.add_cog(SonarCog(bot))
        logging.info("Loaded cog: Sonar")
    except Exception as e:
        logging.error(f"Failed to load cog sonar_cog.py: {str(e)}")
