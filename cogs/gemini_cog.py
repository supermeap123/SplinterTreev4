import discord
from discord.ext import commands
from .base_cog import BaseCog

class GeminiCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemini-Flash",
            nickname="Gemini",
            trigger_words=['gemini', 'flash', 'gemini flash'],
            model="google/gemini-flash-1.5",
            provider="openrouter",
            prompt_file="gemini",
            supports_vision=True
        )

async def setup(bot):
    await bot.add_cog(GeminiCog(bot))
