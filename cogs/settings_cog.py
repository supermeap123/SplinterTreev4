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
        self.activated_channels_file = "activated_channels.json"
        self.name = "Settings"
        
        # Load activated channels on initialization
        self.activated_channels = self.load_activated_channels()

    def load_activated_channels(self):
        """Load activated channels from JSON file"""
        try:
            if os.path.exists(self.activated_channels_file):
                with open(self.activated_channels_file, 'r') as f:
                    channels = json.load(f)
                    logging.info(f"[Settings] Loaded activated channels: {channels}")
                    return channels
            logging.info("[Settings] No activated channels file found, creating new one")
            return {}
        except Exception as e:
            logging.error(f"[Settings] Error loading activated channels: {e}")
            return {}

    def save_activated_channels(self):
        """Save activated channels to JSON file"""
        try:
            with open(self.activated_channels_file, 'w') as f:
                json.dump(self.activated_channels, f, indent=4)
            logging.info(f"[Settings] Saved activated channels: {self.activated_channels}")
        except Exception as e:
            logging.error(f"[Settings] Error saving activated channels: {e}")

    async def handle_message(self, message, full_content=None):
        """Override handle_message to do nothing since SettingsCog doesn't handle messages directly."""
        pass

    @commands.command(name="activate", aliases=["st_activate"])
    @commands.has_permissions(manage_messages=True)
    async def activate_channel(self, ctx):
        """Activate the bot to respond to every message in the current channel"""
        try:
            guild_id = str(ctx.guild.id) if ctx.guild else "dm"
            channel_id = str(ctx.channel.id)

            logging.info(f"[Settings] Activating channel {channel_id} in guild {guild_id}")

            # Initialize guild dict if needed
            if guild_id not in self.activated_channels:
                self.activated_channels[guild_id] = {}

            # Add the channel
            self.activated_channels[guild_id][channel_id] = True
            self.save_activated_channels()

            # Reload activated channels in RouterCog
            router_cog = self.bot.get_cog('RouterCog')
            if router_cog:
                router_cog.activated_channels = self.activated_channels
                logging.info(f"[Settings] Updated RouterCog activated channels: {router_cog.activated_channels}")

            await ctx.reply("✅ Bot will now respond to every message in this channel.")
        except Exception as e:
            logging.error(f"[Settings] Error activating channel: {e}")
            await ctx.reply("❌ Failed to activate channel. Please try again.")

    @commands.command(name="deactivate", aliases=["st_deactivate"])
    @commands.has_permissions(manage_messages=True)
    async def deactivate_channel(self, ctx):
        """Deactivate the bot's response to every message in the current channel"""
        try:
            guild_id = str(ctx.guild.id) if ctx.guild else "dm"
            channel_id = str(ctx.channel.id)

            logging.info(f"[Settings] Deactivating channel {channel_id} in guild {guild_id}")

            # Remove the channel if it exists
            if (guild_id in self.activated_channels and 
                channel_id in self.activated_channels[guild_id]):
                del self.activated_channels[guild_id][channel_id]
                
                # Clean up empty guild dict
                if not self.activated_channels[guild_id]:
                    del self.activated_channels[guild_id]
                
                self.save_activated_channels()

                # Reload activated channels in RouterCog
                router_cog = self.bot.get_cog('RouterCog')
                if router_cog:
                    router_cog.activated_channels = self.activated_channels
                    logging.info(f"[Settings] Updated RouterCog activated channels: {router_cog.activated_channels}")

                await ctx.reply("✅ Bot will no longer respond to every message in this channel.")
            else:
                await ctx.reply("❌ This channel was not previously activated.")
        except Exception as e:
            logging.error(f"[Settings] Error deactivating channel: {e}")
            await ctx.reply("❌ Failed to deactivate channel. Please try again.")

    @commands.command(name="list_activated", aliases=["st_list_activated"])
    @commands.has_permissions(manage_messages=True)
    async def list_activated_channels(self, ctx):
        """List all activated channels"""
        try:
            guild_id = str(ctx.guild.id) if ctx.guild else "dm"
            
            if guild_id in self.activated_channels and self.activated_channels[guild_id]:
                activated_channels = list(self.activated_channels[guild_id].keys())
                channel_mentions = [f"<#{channel_id}>" for channel_id in activated_channels]
                
                await ctx.reply("Activated channels:\n" + "\n".join(channel_mentions))
            else:
                await ctx.reply("No channels are currently activated in this server.")
        except Exception as e:
            logging.error(f"[Settings] Error listing activated channels: {e}")
            await ctx.reply("❌ Failed to list activated channels. Please try again.")

    # Existing methods (set_system_prompt, reset_system_prompt) remain unchanged

async def setup(bot):
    try:
        cog = SettingsCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Settings] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Settings] Failed to register cog: {e}", exc_info=True)
        raise
