import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Gemma(BaseCog, name="Gemma"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, trigger_words=['[Gemma]', '[gemma]'], name="Gemma", model="google/gemma-2-27b-it", provider="openrouter")
        self.temperature = get_model_temperature("Gemma")

    @commands.command(name="gemma", aliases=["Gemma"])
    async def gemma_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Gemma")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(Gemma(bot))
        logging.info("Loaded cog: Gemma")
    except Exception as e:
        logging.error(f"Failed to load cog gemma_cog.py: {str(e)}")
