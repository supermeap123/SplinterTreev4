import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class MOACog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="MOA",
            nickname="MOA",
            trigger_words=["moa"],
            model="openpipe:moa-gpt-4o-v1",
            provider="openpipe",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(MOACog(bot))
