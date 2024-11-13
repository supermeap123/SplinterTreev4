import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog, handled_messages
import json
import re
import random
import os

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],  # Empty since this handles messages without explicit keywords
            model="openpipe:FreeRouter-v2-235",
            provider="openpipe",
            prompt_file="router",
            supports_vision=False
        )
        logging.debug(f"[Router] Initialized")
        logging.debug(f"[Router] Using provider: {self.provider}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Router] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Predefined list of valid models for strict validation
        self.valid_models = [
            "Gemini", "Magnum", "Claude3Haiku", "Nemotron",
            "Sydney", "Sonar", "Ministral", "Sorcerer", "Splintertree",
            "FreeRouter", "Gemma", "Hermes", "Liquid",
            "Llama32_11b", "Llama32_90b", "Mixtral", "Noromaid",
            "Openchat", "Rplus"
        ]

        # Load activated channels
        self.activated_channels = self.load_activated_channels()
        logging.info(f"[Router] Loaded activated channels: {self.activated_channels}")

    def load_activated_channels(self):
        """Load activated channels from JSON file"""
        try:
            activated_channels_file = "activated_channels.json"
            if os.path.exists(activated_channels_file):
                with open(activated_channels_file, 'r') as f:
                    channels = json.load(f)
                    logging.info(f"[Router] Loaded activated channels: {channels}")
                    return channels
            logging.info("[Router] No activated channels file found")
            return {}
        except Exception as e:
            logging.error(f"[Router] Error loading activated channels: {e}")
            return {}

    def is_channel_activated(self, message):
        """Check if the channel is activated for bot responses"""
        try:
            guild_id = str(message.guild.id) if message.guild else "dm"
            channel_id = str(message.channel.id)

            # Check if the channel is activated
            is_activated = (guild_id in self.activated_channels and 
                          channel_id in self.activated_channels[guild_id])
            
            logging.debug(f"[Router] Channel {channel_id} in guild {guild_id} activated: {is_activated}")
            return is_activated
        except Exception as e:
            logging.error(f"[Router] Error checking activated channel: {e}")
            return False

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages in activated channels or with specific triggers"""
        try:
            # Ignore messages from bots
            if message.author.bot:
                logging.debug(f"[Router] Ignoring bot message {message.id}")
                return

            # Skip if message has already been handled
            if message.id in handled_messages:
                logging.debug(f"[Router] Message {message.id} already handled")
                return

            # Check if channel is activated
            is_activated = self.is_channel_activated(message)
            logging.debug(f"[Router] Message {message.id} in activated channel: {is_activated}")

            # Check for trigger words or other conditions
            should_handle = self.should_handle_message(message)
            logging.debug(f"[Router] Message {message.id} should be handled: {should_handle}")

            # Handle message if channel is activated or should be handled
            if is_activated or should_handle:
                logging.info(f"[Router] Handling message {message.id} (activated: {is_activated}, should_handle: {should_handle})")
                handled_messages.add(message.id)
                await self.handle_message(message)
            else:
                logging.debug(f"[Router] Skipping message {message.id}")

        except Exception as e:
            logging.error(f"[Router] Error in on_message: {e}")

    def should_handle_message(self, message):
        """Check if the router should handle this message"""
        try:
            # Check if message has already been handled
            if message.id in handled_messages:
                logging.debug(f"[Router] Message {message.id} already handled")
                return False

            # Check if channel is activated
            if self.is_channel_activated(message):
                logging.debug(f"[Router] Message {message.id} in activated channel")
                return True

            msg_content = message.content.lower()

            # Allow messages from bots only if they mention 'splintertree'
            if message.author.bot:
                should_handle = "splintertree" in msg_content
                logging.debug(f"[Router] Bot message {message.id} should be handled: {should_handle}")
                return should_handle

            # Check if message is a DM
            if isinstance(message.channel, discord.DMChannel):
                logging.debug(f"[Router] Message {message.id} is DM")
                return True

            # Check if bot is mentioned
            if self.bot.user in message.mentions:
                logging.debug(f"[Router] Message {message.id} mentions bot")
                return True

            # Check if a specific role is mentioned
            splintertree_role_id = 1304230846936649762  # Specific role ID
            for role in message.role_mentions:
                if role.id == splintertree_role_id or 'splintertree' in role.name.lower():
                    logging.debug(f"[Router] Message {message.id} mentions role")
                    return True

            # Check if "splintertree" is mentioned
            if "splintertree" in msg_content:
                logging.debug(f"[Router] Message {message.id} mentions splintertree")
                return True

            # Check if message starts with !st_ 
            if msg_content.startswith("!st_"):
                logging.debug(f"[Router] Message {message.id} starts with !st_")
                return True

            logging.debug(f"[Router] Message {message.id} does not meet any handling criteria")
            return False

        except Exception as e:
            logging.error(f"[Router] Error in should_handle_message: {e}")
            return False

async def setup(bot):
    try:
        cog = RouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Router] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Router] Failed to register cog: {e}", exc_info=True)
        raise
