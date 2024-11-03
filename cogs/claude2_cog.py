import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Claude2_cog(BaseCog, name="Claude-2"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Claude-2", model="anthropic/claude-2", provider="openrouter")
        self.temperature = get_model_temperature("Claude-2")

    @commands.command(name="claude2", aliases=["Claude2", "claude-2", "Claude-2"])
    async def claude2_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Claude-2")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Claude2_cog(bot))
        logging.info("Loaded cog: Claude2")
    except Exception as e:
        logging.error(f"Failed to load cog claude2_cog.py: {str(e)}")
