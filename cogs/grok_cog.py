import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Grok_cog(BaseCog, name="Grok"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, trigger_words=['[Grok]', '[grok]'], name="Grok", model="x-ai/grok-beta", provider="openrouter")
        self.temperature = get_model_temperature("Grok")

    @commands.command(name="grok", aliases=["Grok"])
    async def grok_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Grok")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")

async def setup(bot):
    try:
        await bot.add_cog(Grok_cog(bot))
        logging.info("Loaded cog: Grok")
    except Exception as e:
        logging.error(f"Failed to load cog grok_cog.py: {str(e)}")
