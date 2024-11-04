import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class O1MiniCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="O1-Mini",
            nickname="O1Mini",
            trigger_words=['o1mini', 'o1 mini'],
            model="openai/o1-mini",
            provider="openrouter",
            prompt_file="o1mini",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[O1-Mini] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[O1-Mini] Using provider: {self.provider}")
        logging.debug(f"[O1-Mini] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "O1-Mini"

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = O1MiniCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[O1-Mini] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[O1-Mini] Failed to register cog: {str(e)}", exc_info=True)
        raise