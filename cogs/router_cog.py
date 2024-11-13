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

    def load_activated_channels(self):
        """Load activated channels from JSON file"""
        try:
            activated_channels_file = "activated_channels.json"
            if os.path.exists(activated_channels_file):
                with open(activated_channels_file, 'r') as f:
                    return json.load(f)
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
            return (guild_id in self.activated_channels and 
                    channel_id in self.activated_channels[guild_id])
        except Exception as e:
            logging.error(f"[Router] Error checking activated channel: {e}")
            return False

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages in activated channels or with specific triggers"""
        # Ignore messages from bots
        if message.author.bot:
            return

        # Check if channel is activated or message contains trigger words
        if (self.is_channel_activated(message) or 
            any(word in message.content.lower() for word in self.trigger_words)):
            
            # Only handle if not already processed by another cog
            if message.id not in handled_messages:
                handled_messages.add(message.id)
                await self.handle_message(message)

    def should_handle_message(self, message):
        """Check if the router should handle this message"""
        # Check if message has already been handled
        if message.id in handled_messages:
            return False

        # Check if channel is activated
        if self.is_channel_activated(message):
            return True

        msg_content = message.content.lower()

        # Allow messages from bots only if they mention 'splintertree'
        if message.author.bot:
            if "splintertree" in msg_content:
                return True
            else:
                return False

        # Check if message is a DM
        if isinstance(message.channel, discord.DMChannel):
            return True

        # Check if bot is mentioned
        if self.bot.user in message.mentions:
            return True

        # Check if a specific role is mentioned
        splintertree_role_id = 1304230846936649762  # Specific role ID
        for role in message.role_mentions:
            if role.id == splintertree_role_id or 'splintertree' in role.name.lower():
                logging.debug(f"[Router] Role mention detected: {role.name}")
                return True

        # Check if "splintertree" is mentioned
        if "splintertree" in msg_content:
            return True

        # Check if message starts with !st_ 
        if msg_content.startswith("!st_"):
            return True

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
