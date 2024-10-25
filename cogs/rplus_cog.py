import discord
from discord.ext import commands
from .base_cog import BaseCog

class RplusCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="R-Plus",
            nickname="R",
            trigger_words=['rplus', 'r plus', 'r+'],
            model="cohere/command-r-plus",
            provider="openrouter",
            prompt_file="rplus",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(RplusCog(bot))
