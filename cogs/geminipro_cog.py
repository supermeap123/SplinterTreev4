import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Geminipro_cog(BaseCog, name="GeminiPro"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, trigger_words=['[GeminiPro]', '[geminipro]'], name="GeminiPro", model="google/gemini-pro-vision", provider="openrouter", supports_vision=True)
        self.temperature = get_model_temperature("GeminiPro")

    @commands.command(name="geminipro", aliases=["GeminiPro"])
    async def geminipro_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "GeminiPro")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Geminipro_cog(bot))
        logging.info("Loaded cog: GeminiPro")
    except Exception as e:
        logging.error(f"Failed to load cog geminipro_cog.py: {str(e)}")
