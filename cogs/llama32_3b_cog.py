import discord
from discord.ext import commands
from .base_cog import BaseCog

class Llama32_3B_Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama32_3B",
            nickname="Llama3B",
            trigger_words=['llama3b'],
            model="meta-llama/llama-3.2-3b-instruct:free",
            provider="openrouter",
            prompt_file="llama32_3b"
        )

async def setup(bot):
    await bot.add_cog(Llama32_3B_Cog(bot))
