import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from datetime import datetime

class ManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'databases/bot.db'
        self.ensure_database()

    def ensure_database(self):
        os.makedirs('databases', exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        with open('databases/schema.sql', 'r') as schema_file:
            cursor.executescript(schema_file.read())
        
        conn.commit()
        conn.close()

    def has_channel_permissions(self, member: discord.Member) -> bool:
        return member.guild_permissions.manage_channels or member.guild_permissions.manage_messages

    async def handle_activation(self, ctx_or_interaction, activate: bool):
        """Common handler for both slash and legacy commands"""
        # Get the user and check permissions
        user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
        if not self.has_channel_permissions(user):
            response = "You need channel management or message management permissions to use this command."
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(response, ephemeral=True)
            else:
                await ctx_or_interaction.reply(response)
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        channel_id = str(ctx_or_interaction.channel_id)
        guild_id = str(ctx_or_interaction.guild_id)

        if activate:
            # Remove from deactivated channels if present
            cursor.execute('''
                DELETE FROM deactivated_channels 
                WHERE channel_id = ? AND guild_id = ?
            ''', (channel_id, guild_id))
            message = "Bot message processing has been activated in this channel."
        else:
            # Add to deactivated channels
            cursor.execute('''
                INSERT OR REPLACE INTO deactivated_channels (channel_id, guild_id)
                VALUES (?, ?)
            ''', (channel_id, guild_id))
            message = "Bot message processing has been deactivated in this channel."

        conn.commit()
        conn.close()

        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.response.send_message(message, ephemeral=True)
        else:
            await ctx_or_interaction.reply(message)

    @app_commands.command(
        name="activate",
        description="Activate bot message processing in this channel"
    )
    async def activate_slash(self, interaction: discord.Interaction):
        await self.handle_activation(interaction, True)

    @app_commands.command(
        name="deactivate",
        description="Deactivate bot message processing in this channel"
    )
    async def deactivate_slash(self, interaction: discord.Interaction):
        await self.handle_activation(interaction, False)

    @commands.command(name="activate")
    async def activate_legacy(self, ctx):
        """Legacy command to activate bot message processing in this channel"""
        await self.handle_activation(ctx, True)

    @commands.command(name="deactivate")
    async def deactivate_legacy(self, ctx):
        """Legacy command to deactivate bot message processing in this channel"""
        await self.handle_activation(ctx, False)

    def is_channel_active(self, channel_id: str, guild_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 1 FROM deactivated_channels 
            WHERE channel_id = ? AND guild_id = ?
        ''', (channel_id, guild_id))

        result = cursor.fetchone() is None  # Channel is active if it's not in deactivated_channels
        conn.close()
        return result

async def setup(bot):
    await bot.add_cog(ManagementCog(bot))
