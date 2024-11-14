import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class RouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],
            model="openpipe:FreeRouter-v2-235",
            provider="openpipe",
            prompt_file="router",
            supports_vision=False
        )
        logging.debug(f"[Router] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Router] Using provider: {self.provider}")
        logging.debug(f"[Router] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Router] Failed to load temperatures.json: {e}")
            self.temperatures = {}

        # Initialize set to track active channels
        self.active_channels = set()

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Router"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    @commands.command(name='activate')
    @commands.has_permissions(manage_channels=True)
    async def activate(self, ctx):
        """Activate RouterCog in the current channel."""
        channel_id = ctx.channel.id
        self.active_channels.add(channel_id)
        await ctx.send("RouterCog has been activated in this channel.")
        logging.info(f"[Router] Activated in channel {channel_id}")

    @commands.command(name='deactivate')
    @commands.has_permissions(manage_channels=True)
    async def deactivate(self, ctx):
        """Deactivate RouterCog in the current channel."""
        channel_id = ctx.channel.id
        self.active_channels.discard(channel_id)
        await ctx.send("RouterCog has been deactivated in this channel.")
        logging.info(f"[Router] Deactivated in channel {channel_id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listener for incoming messages to generate responses when activated."""
        logging.debug(f"[Router] on_message called for message: '{message.content}' by {message.author}")

        # Prevent the bot from responding to its own messages
        if message.author == self.bot.user:
            logging.debug("[Router] Message from bot itself, ignoring.")
            return

        response = None

        # Check if the channel is active
        if message.channel.id in self.active_channels:
            logging.debug(f"[Router] Channel {message.channel.id} is active. Generating response.")
            response = await self.generate_response(message)
        else:
            # Additionally, respond to DMs, mentions, and role mentions
            if isinstance(message.channel, discord.DMChannel):
                logging.debug("[Router] Message is a DM. Generating response.")
                response = await self.generate_response(message)
            elif self.bot.user in message.mentions:
                logging.debug("[Router] Bot was mentioned. Generating response.")
                response = await self.generate_response(message)
            elif any(role.mention in message.content for role in message.role_mentions):
                logging.debug("[Router] Role was mentioned. Generating response.")
                response = await self.generate_response(message)

        if response:
            logging.debug(f"[Router] Sending response: {response}")
            await message.channel.send(response)
        else:
            logging.debug("[Router] No response generated.")

        # Ensure that other commands are still processed
        await self.bot.process_commands(message)

    async def generate_response(self, message):
        """Generate a fixed response for testing purposes"""
        try:
            # Return a fixed response to verify activation works
            return "Test response"
        except Exception as e:
            logging.error(f"Error generating test response for Router: {e}")
            return None

    async def cog_check(self, ctx):
        """Ensure that commands are only used in guilds."""
        return ctx.guild is not None

async def setup(bot):
    try:
        cog = RouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Router] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Router] Failed to register cog: {e}", exc_info=True)
        raise
