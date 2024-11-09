import discord
from discord.ext import commands
import json
import logging
import os
from .base_cog import BaseCog

class SettingsCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Settings",
            nickname="Settings",
            trigger_words=[],  # No trigger words since it handles commands only
            model="",          # No model associated
            provider="",       # No provider
            prompt_file=None,  # No prompt file
            supports_vision=False
        )
        self.dynamic_prompts_file = "dynamic_prompts.json"
        self.name = "Settings"

    async def handle_message(self, message, full_content=None):
        """Override handle_message to do nothing since SettingsCog doesn't handle messages directly."""
        pass

    @commands.command(name="st_set_system_prompt")
    @commands.has_permissions(manage_messages=True)
    async def st_set_system_prompt(self, ctx, agent: str, *, prompt: str):
        """Set a custom system prompt for an AI agent in this channel"""
        try:
            # Load existing prompts
            if os.path.exists(self.dynamic_prompts_file):
                with open(self.dynamic_prompts_file, "r") as f:
                    dynamic_prompts = json.load(f)
            else:
                dynamic_prompts = {}

            # Get guild and channel IDs
            guild_id = str(ctx.guild.id) if ctx.guild else None
            channel_id = str(ctx.channel.id)

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

            await ctx.reply(f"✅ System prompt updated for {agent} in this channel.")

        except Exception as e:
            logging.error(f"Error setting system prompt: {str(e)}")
            await ctx.reply("❌ Failed to set system prompt. Please try again.")

    @commands.command(name="st_reset_system_prompt")
    @commands.has_permissions(manage_messages=True)
    async def st_reset_system_prompt(self, ctx, agent: str):
        """Reset the system prompt for an AI agent to its default in this channel"""
        try:
            if not os.path.exists(self.dynamic_prompts_file):
                await ctx.reply("No custom prompts found.")
                return

            with open(self.dynamic_prompts_file, "r") as f:
                dynamic_prompts = json.load(f)

            guild_id = str(ctx.guild.id) if ctx.guild else None
            channel_id = str(ctx.channel.id)

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

            await ctx.reply(f"✅ System prompt reset to default for {agent} in this channel.")

        except Exception as e:
            logging.error(f"Error resetting system prompt: {str(e)}")
            await ctx.reply("❌ Failed to reset system prompt. Please try again.")

    async def setup(bot):
        await bot.add_cog(SettingsCog(bot))
