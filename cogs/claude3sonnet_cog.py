import discord
from discord.ext import commands
import logging

from base_cog import BaseCog
from shared.utils import get_model_temperature

class Claude3Sonnet(BaseCog, name="Claude-3.5-Sonnet"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, name="Claude-3.5-Sonnet", model="anthropic/claude-3.5-sonnet", provider="openrouter")
        self.temperature = get_model_temperature("Claude-3.5-Sonnet")

    @commands.command(name="claude3sonnet", aliases=["Claude3Sonnet", "claude3.5sonnet", "Claude3.5Sonnet", "claude-3.5-sonnet", "Claude-3.5-Sonnet"])
    async def claude3sonnet_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Claude-3.5-Sonnet")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{cog.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(Claude3Sonnet(bot))
        logging.info("Loaded cog: Claude3Sonnet")
    except Exception as e:
        logging.error(f"Failed to load cog claude3sonnet_cog.py: {str(e)}")
