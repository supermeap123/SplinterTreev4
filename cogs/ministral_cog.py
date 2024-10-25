import discord
from discord.ext import commands
from .base_cog import BaseCog

class MinistralCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Ministral",
            nickname="Ministral",
            trigger_words=['ministral', 'mistral', 'ministral ai', "m8b"],
            model="mistralai/ministral-8b",
            provider="openrouter",
            prompt_file="ministral",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(MinistralCog(bot))
