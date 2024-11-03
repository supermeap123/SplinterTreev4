import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Claude1_1(BaseCog, name="Claude-1.1"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, trigger_words=['[Claude-1.1]', '[claude-1.1]', '[Claude1.1]', '[claude1.1]'], name="Claude-1.1", model="anthropic/claude-instant-1.1", provider="openrouter")
        self.temperature = get_model_temperature("Claude-1.1")

    @commands.command(name="claude1_1", aliases=["Claude1_1", "claude1.1", "Claude1.1", "claude-1.1", "Claude-1.1"])
    async def claude1_1_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Claude-1.1")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(Claude1_1(bot))
        logging.info("Loaded cog: Claude1_1")
    except Exception as e:
        logging.error(f"Failed to load cog claude1_1_cog.py: {str(e)}")
