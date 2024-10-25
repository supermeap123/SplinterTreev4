import discord
from discord.ext import commands
from .base_cog import BaseCog

class OpenchatCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="OpenChat",
            nickname="OpenChat",
            trigger_words=['openchat', 'open chat'],
            model="openchat/openchat-7b:free",
            provider="openrouter",
            prompt_file="openchat",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(OpenchatCog(bot))
