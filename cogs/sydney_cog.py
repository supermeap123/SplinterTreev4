import discord
from discord.ext import commands
import logging
from base_cog import BaseCog
from shared.utils import get_model_temperature

class Sydney(BaseCog, name="Sydney"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)
        self.temperature = get_model_temperature("Sydney")

    @commands.command(name="sydney", aliases=["Sydney"])
    async def sydney_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Sydney")

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandInvokeError):
            logging.error(f"[Sydney] {error.original}", exc_info=True)
        else:
            await super().cog_command_error(ctx, error)

    async def cog_load(self):
        try:
            await super().cog_load()
            logging.info(f"[Sydney] Registered cog with qualified_name: {self.qualified_name}")
        except Exception as e:
            logging.error(f"[Sydney] Failed to register cog: {str(e)}", exc_info=True)
            raise

def setup(bot: commands.Bot):
    try:
        bot.add_cog(Sydney(bot))
        logging.info("Loaded cog: Sydney")
    except Exception as e:
        logging.error(f"Failed to load Sydney cog: {str(e)}", exc_info=True)
