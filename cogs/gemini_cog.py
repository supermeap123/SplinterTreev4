import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Gemini(BaseCog, name="Gemini"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Gemini", model="google/gemini-pro-1.5", provider="openrouter")  # Assuming "Gemini" refers to gemini-pro-1.5
        self.temperature = get_model_temperature("Gemini")

    @commands.command(name="gemini", aliases=["Gemini"])
    async def gemini_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Gemini")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(Gemini(bot))
        logging.info("Loaded cog: Gemini")
    except Exception as e:
        logging.error(f"Failed to load cog gemini_cog.py: {str(e)}")
