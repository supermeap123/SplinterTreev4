import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class O1mini_cog(BaseCog, name="O1Mini"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="O1Mini", model="openai/o1-mini", provider="openrouter")
        self.temperature = get_model_temperature("O1Mini")

    @commands.command(name="o1mini", aliases=["O1Mini"])
    async def o1mini_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "O1Mini")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(O1mini_cog(bot))
        logging.info("Loaded cog: O1Mini")
    except Exception as e:
        logging.error(f"Failed to load cog o1mini_cog.py: {str(e)}")
