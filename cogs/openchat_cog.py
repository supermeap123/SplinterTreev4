import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class OpenChat(BaseCog, name="OpenChat"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="OpenChat", model="openchat/openchat-7b", provider="openrouter")
        self.temperature = get_model_temperature("OpenChat")

    @commands.command(name="openchat", aliases=["OpenChat"])
    async def openchat_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "OpenChat")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(OpenChat(bot))
        logging.info("Loaded cog: OpenChat")
    except Exception as e:
        logging.error(f"Failed to load cog openchat_cog.py: {str(e)}")
