import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
import os
from config import DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW, CONTEXT_WINDOWS

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dynamic_prompts_file = "dynamic_prompts.json"
        self.context_settings_file = "context_settings.json"
        self.name = "Settings"
        self._load_context_settings()

    def _load_context_settings(self):
        """Load context window settings from file"""
        try:
            if os.path.exists(self.context_settings_file):
                with open(self.context_settings_file, 'r') as f:
                    settings = json.load(f)
                    # Update global CONTEXT_WINDOWS
                    CONTEXT_WINDOWS.clear()
                    CONTEXT_WINDOWS.update(settings)
        except Exception as e:
            logging.error(f"Error loading context settings: {str(e)}")

    def _save_context_settings(self):
        """Save context window settings to file"""
        try:
            with open(self.context_settings_file, 'w') as f:
                json.dump(CONTEXT_WINDOWS, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving context settings: {str(e)}")

    @commands.command(name="setcontext")
    @commands.has_permissions(manage_messages=True)
    async def setcontext_command(self, ctx, size: int):
        """Set the context window size for the current channel (Legacy command)"""
        try:
            if size < 1 or size > MAX_CONTEXT_WINDOW:
                await ctx.reply(f"❌ Context window size must be between 1 and {MAX_CONTEXT_WINDOW}")
                return

            channel_id = str(ctx.channel.id)
            CONTEXT_WINDOWS[channel_id] = size
            self._save_context_settings()

            await ctx.reply(f"✅ Context window size set to {size} messages for this channel")

        except Exception as e:
            logging.error(f"Error setting context window: {str(e)}")
            await ctx.reply("❌ Failed to set context window size. Please try again.")

    @app_commands.command(
        name="set_context_window",
        description="Set the number of messages to keep in context for this channel"
    )
    @app_commands.describe(
        size="Number of messages to keep in context (1-50)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def set_context_window(
        self,
        interaction: discord.Interaction,
        size: int
    ):
        """Set the context window size for the current channel (Slash command)"""
        try:
            if size < 1 or size > MAX_CONTEXT_WINDOW:
                await interaction.response.send_message(
                    f"❌ Context window size must be between 1 and {MAX_CONTEXT_WINDOW}",
                    ephemeral=True
                )
                return

            channel_id = str(interaction.channel.id)
            CONTEXT_WINDOWS[channel_id] = size
            self._save_context_settings()

            await interaction.response.send_message(
                f"✅ Context window size set to {size} messages for this channel",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error setting context window: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to set context window size. Please try again.",
                ephemeral=True
            )

    @commands.command(name="getcontext")
    async def getcontext_command(self, ctx):
        """Get the current context window size for the channel (Legacy command)"""
        try:
            channel_id = str(ctx.channel.id)
            size = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
            
            await ctx.reply(
                f"📝 Current context window size: {size} messages\n" +
                f"(Default size is {DEFAULT_CONTEXT_WINDOW} messages)"
            )

        except Exception as e:
            logging.error(f"Error getting context window: {str(e)}")
            await ctx.reply("❌ Failed to get context window size. Please try again.")

    @app_commands.command(
        name="get_context_window",
        description="View the current context window size for this channel"
    )
    async def get_context_window(self, interaction: discord.Interaction):
        """Get the current context window size for the channel (Slash command)"""
        try:
            channel_id = str(interaction.channel.id)
            size = CONTEXT_WINDOWS.get(channel_id, DEFAULT_CONTEXT_WINDOW)
            
            await interaction.response.send_message(
                f"📝 Current context window size: {size} messages\n" +
                f"(Default size is {DEFAULT_CONTEXT_WINDOW} messages)",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error getting context window: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to get context window size. Please try again.",
                ephemeral=True
            )

    @commands.command(name="resetcontext")
    @commands.has_permissions(manage_messages=True)
    async def resetcontext_command(self, ctx):
        """Reset the context window size to default for the current channel (Legacy command)"""
        try:
            channel_id = str(ctx.channel.id)
            if channel_id in CONTEXT_WINDOWS:
                del CONTEXT_WINDOWS[channel_id]
                self._save_context_settings()

            await ctx.reply(f"✅ Context window size reset to default ({DEFAULT_CONTEXT_WINDOW} messages)")

        except Exception as e:
            logging.error(f"Error resetting context window: {str(e)}")
            await ctx.reply("❌ Failed to reset context window size. Please try again.")

    @app_commands.command(
        name="reset_context_window",
        description="Reset the context window size to default for this channel"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def reset_context_window(self, interaction: discord.Interaction):
        """Reset the context window size to default for the current channel (Slash command)"""
        try:
            channel_id = str(interaction.channel.id)
            if channel_id in CONTEXT_WINDOWS:
                del CONTEXT_WINDOWS[channel_id]
                self._save_context_settings()

            await interaction.response.send_message(
                f"✅ Context window size reset to default ({DEFAULT_CONTEXT_WINDOW} messages)",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Error resetting context window: {str(e)}")
            await interaction.response.send_message(
                "❌ Failed to reset context window size. Please try again.",
                ephemeral=True
            )

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
