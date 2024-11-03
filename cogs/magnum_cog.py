import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Magnum_cog(BaseCog, name="Magnum"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Magnum", model="anthracite-org/magnum-v4-72b", provider="openrouter")
        self.temperature = get_model_temperature("Magnum")

    @commands.command(name="magnum", aliases=["Magnum"])
    async def magnum_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Magnum")


    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Magnum_cog(bot))
        logging.info("Loaded cog: Magnum")
    except Exception as e:
        logging.error(f"Failed to load cog magnum_cog.py: {str(e)}")
