import discord
from discord.ext import commands
from .base_cog import BaseCog

class Claude11Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-1.1",
            nickname="Claude1.1",
            trigger_words=['claude1.1', 'claude 1.1', 'claude1', 'claude 1'],
            model="anthropic/claude-instant-1.1",
            provider="openrouter",
            prompt_file="claude",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(Claude11Cog(bot))
