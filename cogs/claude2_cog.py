import discord
from discord.ext import commands
from .base_cog import BaseCog

class Claude2Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-2",
            nickname="Claude2",
            trigger_words=['claude2', 'claude 2'],
            model="anthropic/claude-2",
            provider="openrouter",
            prompt_file="claude",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(Claude2Cog(bot))
