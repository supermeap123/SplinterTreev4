import discord
from discord.ext import commands
from .base_cog import BaseCog

class GeminiCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemini",
            nickname="Gemini",
            trigger_words=['gemini', 'gemini hi'],
            model="google/gemini-pro-1.5",
            provider="openrouter",
            prompt_file="gemini"
        )

async def setup(bot):
    await bot.add_cog(GeminiCog(bot))
