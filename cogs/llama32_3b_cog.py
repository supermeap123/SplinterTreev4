import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Llama32_3B(BaseCog, name="Llama32_3B"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Llama32_3B", model="meta-llama/llama-3.2-3b-instruct", provider="openrouter")
        self.temperature = get_model_temperature("Llama32_3B")

    @commands.command(name="llama32_3b", aliases=["Llama32_3B"])
    async def llama32_3b_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Llama32_3B")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")

def setup(bot):
    try:
        bot.add_cog(Llama32_3B(bot))
        logging.info("Loaded cog: Llama32_3B")
    except Exception as e:
        logging.error(f"Failed to load Llama32_3B cog: {str(e)}")
