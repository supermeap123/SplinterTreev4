import discord
from discord.ext import commands
from .base_cog import BaseCog

class SonarCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Sonar",
            nickname="Sonar",
            trigger_words=['sonar', 'sonar ai'],
            model="perplexity/llama-3.1-sonar-huge-128k-online",
            provider="openrouter",
            prompt_file="sonar",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(SonarCog(bot))
