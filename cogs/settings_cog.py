import discord
from discord.ext import commands
import config
import logging

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='toggle_shared_history')
    async def toggle_shared_history(self, ctx):
        """Toggle shared history on/off"""
        try:
            config.SHARED_HISTORY_ENABLED = not getattr(config, 'SHARED_HISTORY_ENABLED', False)
            status = "enabled" if config.SHARED_HISTORY_ENABLED else "disabled"
            await ctx.send(f"✅ Shared history has been {status}.")
            logging.info(f"Shared history toggled to {status} by user {ctx.author.name}")
        except Exception as e:
            logging.error(f"Error toggling shared history: {str(e)}")
            await ctx.send("❌ An error occurred while toggling shared history.")

    @commands.command(name='toggle_image_processing')
    async def toggle_image_processing(self, ctx):
        """Toggle image processing on/off"""
        try:
            config.IMAGE_PROCESSING_ENABLED = not getattr(config, 'IMAGE_PROCESSING_ENABLED', False)
            status = "enabled" if config.IMAGE_PROCESSING_ENABLED else "disabled"
            await ctx.send(f"✅ Image processing has been {status}.")
            logging.info(f"Image processing toggled to {status} by user {ctx.author.name}")
        except Exception as e:
            logging.error(f"Error toggling image processing: {str(e)}")
            await ctx.send("❌ An error occurred while toggling image processing.")

async def setup(bot):
    await bot.add_cog(SettingsCog(bot))
