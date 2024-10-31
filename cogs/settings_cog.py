import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
import os

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dynamic_prompts_file = "dynamic_prompts.json"

    @app_commands.command(
        name="set_system_prompt",
        description="Set a custom system prompt for an AI agent in this channel"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def set_system_prompt(
        self,
        interaction: discord.Interaction,
        agent: str,
        prompt: str
    ):
        """Set a custom system prompt for an AI agent in the current channel"""
        try:
            # Load existing prompts
            if os.path.exists(self.dynamic_prompts_file):
                with open(self.dynamic_prompts_file, "r") as f:
                    dynamic_prompts = json.load(f)
            else:
                dynamic_prompts = {}

            # Get guild and channel IDs
            guild_id = str(interaction.guild.id) if interaction.guild else None
            channel_id = str(interaction.channel.id)

            # Initialize guild dict if needed
            if guild_id and guild_id not in dynamic_prompts:
                dynamic_prompts[guild_id] = {}

            # Set the prompt
            if guild_id:
                dynamic_prompts[guild_id][channel_id] = prompt
            else:
                dynamic_prompts[channel_id] = prompt

            # Save updated prompts
            with open(self.dynamic_prompts_file, "w") as f:
                json.dump(dynamic_prompts, f, indent=4)

            await interaction.response.send_message(f"✅ System prompt updated for {agent} in this channel.", ephemeral=True)

        except Exception as e:
            logging.error(f"Error setting system prompt: {str(e)}")
            await interaction.response.send_message("❌ Failed to set system prompt. Please try again.", ephemeral=True)

    @app_commands.command(
        name="reset_system_prompt",
        description="Reset the system prompt for an AI agent to its default in this channel"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def reset_system_prompt(
        self,
        interaction: discord.Interaction,
        agent: str
    ):
        """Reset the system prompt for an AI agent to its default in the current channel"""
        try:
            if not os.path.exists(self.dynamic_prompts_file):
                await interaction.response.send_message("No custom prompts found.", ephemeral=True)
                return

            with open(self.dynamic_prompts_file, "r") as f:
                dynamic_prompts = json.load(f)

            guild_id = str(interaction.guild.id) if interaction.guild else None
            channel_id = str(interaction.channel.id)

            # Remove prompt if it exists
            if guild_id and guild_id in dynamic_prompts:
                if channel_id in dynamic_prompts[guild_id]:
                    del dynamic_prompts[guild_id][channel_id]
                    if not dynamic_prompts[guild_id]:  # Remove guild if empty
                        del dynamic_prompts[guild_id]
            elif channel_id in dynamic_prompts:
                del dynamic_prompts[channel_id]

            # Save updated prompts
            with open(self.dynamic_prompts_file, "w") as f:
                json.dump(dynamic_prompts, f, indent=4)

            await interaction.response.send_message(f"✅ System prompt reset to default for {agent} in this channel.", ephemeral=True)

        except Exception as e:
            logging.error(f"Error resetting system prompt: {str(e)}")
            await interaction.response.send_message("❌ Failed to reset system prompt. Please try again.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SettingsCog(bot))
