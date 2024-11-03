import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class Context_cog(BaseCog, name="ContextCog"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @commands.command(name="context", aliases=["Context"])
    async def context_command(self, ctx: commands.Context):
        await self.process_command(ctx, "context", "ContextCog")

    async def cog_load(self):
        try:
            await super().cog_load()
            logging.info(f"[ContextCog] Registered cog with qualified_name: {self.qualified_name}")
        except Exception as e:
            logging.error(f"[ContextCog] Failed to register cog: {str(e)}")
            raise

async def setup(bot: commands.Bot):
    try:
        await await bot.add_cog(Context_cog(bot))
        logging.info("Loaded core cog: context_cog")
    except Exception as e:
        logging.error(f"Failed to load core cog context_cog: {str(e)}")
