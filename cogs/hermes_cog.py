import discord
from discord.ext import commands
from .base_cog import BaseCog

class HermesCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Hermes-3",
            nickname="Hermes",
            trigger_words=['hermes', 'nous', 'hermes 3'],
            model="nousresearch/hermes-3-llama-3.1-405b:free",
            provider="openrouter",
            prompt_file="hermes",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(HermesCog(bot))
