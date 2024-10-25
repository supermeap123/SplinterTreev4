import discord
from discord.ext import commands
from .base_cog import BaseCog

class MagnumCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Magnum",
            nickname="Magnum",
            trigger_words=['magnum', 'magnum ai'],
            model="anthracite-org/magnum-v4-72b",
            provider="openrouter",
            prompt_file="magnum",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(MagnumCog(bot))
