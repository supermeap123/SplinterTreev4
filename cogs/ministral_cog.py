import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Ministral_cog(BaseCog, name="MiniMistral"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="MiniMistral", model="mistralai/mistral-7b-instruct", provider="openrouter")
        self.temperature = get_model_temperature("MiniMistral")

    @commands.command(name="minimistral", aliases=["MiniMistral"])
    async def minimistral_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "MiniMistral")


    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Ministral_cog(bot))
        logging.info("Loaded cog: MiniMistral")
    except Exception as e:
        logging.error(f"Failed to load cog ministral_cog.py: {str(e)}")
