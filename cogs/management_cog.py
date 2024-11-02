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

    @app_commands.command(
        name="activate",
        description="Activate bot message processing in this channel"
    )
    async def activate(self, interaction: discord.Interaction):
        if not self.has_channel_permissions(interaction.user):
            await interaction.response.send_message("You need channel management or message management permissions to use this command.", ephemeral=True)
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Remove from deactivated channels if present
        cursor.execute('''
            DELETE FROM deactivated_channels 
            WHERE channel_id = ? AND guild_id = ?
        ''', (str(interaction.channel_id), str(interaction.guild_id)))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Bot message processing has been activated in this channel.", ephemeral=True)

    @app_commands.command(
        name="deactivate",
        description="Deactivate bot message processing in this channel"
    )
    async def deactivate(self, interaction: discord.Interaction):
        if not self.has_channel_permissions(interaction.user):
            await interaction.response.send_message("You need channel management or message management permissions to use this command.", ephemeral=True)
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add to deactivated channels
        cursor.execute('''
            INSERT OR REPLACE INTO deactivated_channels (channel_id, guild_id)
            VALUES (?, ?)
        ''', (str(interaction.channel_id), str(interaction.guild_id)))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f"Bot message processing has been deactivated in this channel.", ephemeral=True)

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
