import discord
from discord.ext import commands
import logging

from base_cog import BaseCog
from shared.utils import get_model_temperature

class Nemotron(BaseCog, name="Nemotron"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Nemotron", model="nvidia/llama-3.1-nemotron-70b-instruct", provider="openrouter")
        self.temperature = get_model_temperature("Nemotron")

    @commands.command(name="nemotron", aliases=["Nemotron"])
    async def nemotron_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Nemotron")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{cog.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(Nemotron(bot))
        logging.info("Loaded cog: Nemotron")
    except Exception as e:
        logging.error(f"Failed to load cog nemotron_cog.py: {str(e)}")
