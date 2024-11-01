import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class MoaCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="MOA",
            nickname="moa",
            trigger_words=['moa'],
            model="openpipe:moa-gpt-4o-v1",
            provider="openpipe",
            prompt_file="consolidated_prompts",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[{self.name}] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[{self.name}] Using provider: {self.provider}")
        logging.debug(f"[{self.name}] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return self.name

    # Removed redundant on_message handler - using base_cog's handle_message

async def setup(bot):
    try:
        logging.info(f"[MOA] Starting cog setup...")
        cog = MoaCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
        return cog
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
        raise
