import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Noromaid_cog(BaseCog, name="Noromaid"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Noromaid", model="neversleep/noromaid-20b", provider="openrouter")
        self.temperature = get_model_temperature("Noromaid")

    @commands.command(name="noromaid", aliases=["Noromaid"])
    async def noromaid_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Noromaid")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Noromaid_cog(bot))
        logging.info("Loaded cog: Noromaid")
    except Exception as e:
        logging.error(f"Failed to load cog noromaid_cog.py: {str(e)}")
