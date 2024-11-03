import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Moa_cog(BaseCog, name="Moa"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Moa", model="anthropic/claude-2", provider="openrouter")
        self.temperature = get_model_temperature("Moa")

    @commands.command(name="moa", aliases=["Moa"])
    async def moa_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Moa")


    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Moa_cog(bot))
        logging.info("Loaded cog: Moa")
    except Exception as e:
        logging.error(f"Failed to load cog moa_cog.py: {str(e)}")
