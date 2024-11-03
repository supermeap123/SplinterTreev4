import discord
from discord.ext import commands
import logging
import sqlite3
from .base_cog import BaseCog

class Management_cog(BaseCog, name="ManagementCog"):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

    @commands.command(name="deactivate")
    @commands.has_permissions(administrator=True)
    async def deactivate_command(self, ctx: commands.Context):
        """Deactivate bot responses in the current channel"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO deactivated_channels (channel_id, guild_id)
                VALUES (?, ?)
            ''', (str(ctx.channel.id), str(ctx.guild.id)))
            conn.commit()
            conn.close()
            await ctx.send(f"Bot responses deactivated in {ctx.channel.mention}")
        except Exception as e:
            logging.error(f"Error deactivating channel: {str(e)}")
            await ctx.send("Failed to deactivate bot responses")

    @commands.command(name="activate")
    @commands.has_permissions(administrator=True)
    async def activate_command(self, ctx: commands.Context):
        """Activate bot responses in the current channel"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM deactivated_channels 
                WHERE channel_id = ? AND guild_id = ?
            ''', (str(ctx.channel.id), str(ctx.guild.id)))
            conn.commit()
            conn.close()
            await ctx.send(f"Bot responses activated in {ctx.channel.mention}")
        except Exception as e:
            logging.error(f"Error activating channel: {str(e)}")
            await ctx.send("Failed to activate bot responses")

    async def cog_load(self):
        try:
            await super().cog_load()
            logging.info(f"[ManagementCog] Registered cog with qualified_name: {self.qualified_name}")
        except Exception as e:
            logging.error(f"[ManagementCog] Failed to register cog: {str(e)}")
            raise

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(Management_cog(bot))
        logging.info("Loaded core cog: management_cog")
    except Exception as e:
        logging.error(f"Failed to load core cog management_cog: {str(e)}")
