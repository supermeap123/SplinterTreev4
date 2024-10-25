import discord
from discord.ext import commands
from .base_cog import BaseCog

class O1miniCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="O1-Mini",
            nickname="O1",
            trigger_words=['o1mini', 'o1-mini', 'o1 mini'],
            model="01-ai/yi-6b-chat:free",
            provider="openrouter",
            prompt_file="o1mini",
            supports_vision=False
        )

async def setup(bot):
    await bot.add_cog(O1miniCog(bot))
