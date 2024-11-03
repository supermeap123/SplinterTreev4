import discord
from discord.ext import commands
from .base_cog import BaseCog

class GrokCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Grok",
            nickname="Grok",
            trigger_words=['grok', 'grok beta', 'xai'],
            model="x-ai/grok-beta",
            provider="openrouter",
            prompt_file="grok"
        )

async def setup(bot):
    await bot.add_cog(GrokCog(bot))
