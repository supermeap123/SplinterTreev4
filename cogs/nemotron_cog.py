import discord
from discord.ext import commands
from .base_cog import BaseCog

class NemotronCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Nemotron",
            nickname="Nemotron",
            trigger_words=['nemotron', 'nemo', 'nemotron ai'],
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            provider="openrouter",
            prompt_file="nemotron",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(NemotronCog(bot))
