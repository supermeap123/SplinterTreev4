import discord
from discord.ext import commands
import logging

from .base_cog import BaseCog
from shared.utils import get_model_temperature

class Llama32_11b_cog(BaseCog, name="Llama32_11B"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot, trigger_words=['[Llama32_11B]', '[llama32_11b]'], name="Llama32_11B", model="meta-llama/llama-3.2-11b-vision-instruct", provider="openrouter", supports_vision=True)
        self.temperature = get_model_temperature("Llama32_11B")

    @commands.command(name="llama32_11b", aliases=["Llama32_11B"])
    async def llama32_11b_command(self, ctx: commands.Context, *, prompt: str):
        await self.process_command(ctx, prompt, "Llama32_11B")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{self.name}] Failed to register cog: {str(e)}")


async def setup(bot):
    try:
        await bot.add_cog(Llama32_11b_cog(bot))
        logging.info("Loaded cog: Llama32_11B")
    except Exception as e:
        logging.error(f"Failed to load cog llama32_11b_cog.py: {str(e)}")
