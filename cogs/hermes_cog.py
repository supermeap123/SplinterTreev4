import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Hermes(BaseCog, name="Hermes"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Hermes", model="nousresearch/hermes-3-llama-3.1-405b", provider="openrouter")
        self.temperature = get_model_temperature("Hermes")

    @commands.command(name="hermes", aliases=["Hermes"])
    async def hermes_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Hermes")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(Hermes(bot))
        logging.info("Loaded cog: Hermes")
    except Exception as e:
        logging.error(f"Failed to load cog hermes_cog.py: {str(e)}")
