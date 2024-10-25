import discord
from discord.ext import commands
from .base_cog import BaseCog

class GemmaCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemma",
            nickname="Gemma",
            trigger_words=['gemma', 'gemma ai'],
            model="google/gemma-2-9b-it:free",
            provider="openrouter",
            prompt_file="gemma",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(GemmaCog(bot))
