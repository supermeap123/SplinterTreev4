import discord
from discord.ext import commands
import logging

from base_cog import BaseCog
from shared.utils import get_model_temperature

class RPlus(BaseCog, name="RPlus"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="RPlus", model="cohere/command-r-plus", provider="openrouter")
        self.temperature = get_model_temperature("RPlus")

    @commands.command(name="rplus", aliases=["RPlus"])
    async def rplus_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "RPlus")


    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{cog.name}] Failed to register cog: {str(e)}")



def setup(bot):
    try:
        bot.add_cog(RPlus(bot))
        logging.info("Loaded cog: RPlus")
    except Exception as e:
        logging.error(f"Failed to load cog rplus_cog.py: {str(e)}")
