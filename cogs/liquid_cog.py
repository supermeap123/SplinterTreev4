import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Liquid_cog(BaseCog, name="Liquid"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Liquid", model="liquid/lfm-40b", provider="openrouter")
        self.temperature = get_model_temperature("Liquid")

    @commands.command(name="liquid", aliases=["Liquid"])
    async def liquid_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Liquid")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")

async def setup(bot):
    try:
        await bot.add_cog(Liquid_cog(bot))
        logging.info("Loaded cog: Liquid")
    except Exception as e:
        logging.error(f"Failed to load cog liquid_cog.py: {str(e)}")
