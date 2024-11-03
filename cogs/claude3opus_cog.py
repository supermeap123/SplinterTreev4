import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Claude3opus_cog(BaseCog, name="Claude-3-Opus"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, trigger_words=['[Claude-3-Opus]', '[claude-3-opus]', '[Claude3Opus]', '[claude3opus]'], name="Claude-3-Opus", model="anthropic/claude-3-opus", provider="openrouter")
        self.temperature = get_model_temperature("Claude-3-Opus")

    @commands.command(name="claude3opus", aliases=["Claude3Opus", "claude3.0opus", "Claude3.0Opus", "claude-3-opus", "Claude-3-Opus"])
    async def claude3opus_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Claude-3-Opus")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await await bot.add_cog(Claude3opus_cog(bot))
        logging.info("Loaded cog: Claude3Opus")
    except Exception as e:
        logging.error(f"Failed to load cog claude3opus_cog.py: {str(e)}")
