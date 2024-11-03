import discord
from discord.ext import commands
import logging

from base_cog import BaseCog
from shared.utils import get_token_count, set_temperature, set_model

class SettingsCog(BaseCog, name="SettingsCog"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @commands.command(name="temp", aliases=["temperature"])
    async def temp_command(self, ctx: commands.Context, model: str, temp: float):
        try:
            if set_temperature(model, temp):
                await ctx.send(f"✅ Set temperature for {model} to {temp}")
            else:
                await ctx.send(f"❌ Invalid temperature for {model}. Use !temps to see valid ranges.")
        except Exception as e:
            logging.error(f"Error setting temperature: {str(e)}")
            await ctx.send("❌ An error occurred while setting the temperature.")

    @commands.command(name="temps", aliases=["temperatures"])
    async def temps_command(self, ctx: commands.Context):
        try:
            with open('temperatures.json', 'r') as f:
                temps = json.load(f)
            
            embed = discord.Embed(title="Model Temperatures", description="Current temperature settings:", color=discord.Color.blue())
            
            for model, temp_range in temps.items():
                embed.add_field(name=model, value=f"Current: {temp_range['current']}\nRange: {temp_range['min']} - {temp_range['max']}", inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            logging.error(f"Error displaying temperatures: {str(e)}")
            await ctx.send("❌ An error occurred while fetching temperatures.")

    async def cog_load(self):
        try:
            await super().cog_load()
        except Exception as e:
            logging.error(f"[{cog.name}] Failed to register cog: {str(e)}")


def setup(bot):
    try:
        bot.add_cog(SettingsCog(bot))
        logging.info("Loaded settings cog")
    except Exception as e:
        logging.error(f"Failed to load settings cog: {str(e)}")
