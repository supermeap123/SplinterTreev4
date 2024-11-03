import discord
from discord.ext import commands
import logging
from base_cog import BaseCog
from shared.utils import get_token_count, set_temperature, set_model

class SettingsCog(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)

        self.default_temperature = 0.3

    @commands.command(name='temperature', aliases=['temp'], help='Set the temperature for the model')
    async def temperature(self, ctx, temperature: float):
        try:
            if 0 <= temperature <= 2:
                set_temperature(ctx.guild.id, temperature)
                await ctx.send(f"Temperature set to {temperature}")
            else:
                await ctx.send("Temperature must be between 0 and 2")
        except Exception as e:
            logging.exception(f"Failed to set temperature: {e}")
            await ctx.send("Failed to set temperature. Please check the logs.")

    @commands.command(name='model', help='Set the AI model')
    async def model(self, ctx, model_name: str):
        try:
            # Assuming there's a way to validate model_name
            if self.bot.model_exists(model_name):  # Placeholder for model validation
                set_model(ctx.guild.id, model_name)
                await ctx.send(f"Model set to {model_name}")
            else:
                await ctx.send("Invalid model name.")
        except Exception as e:
            logging.exception(f"Failed to set model: {e}")
            await ctx.send("Failed to set model. Please check the logs.")


async def setup(bot):
    cog = SettingsCog(bot)
    try:
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
