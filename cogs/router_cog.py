import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class RouterCog(BaseCog):
    # Dictionary to track activation status per channel
    active_channels = {}

    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Router",
            nickname="Router",
            trigger_words=[],  # Match all messages
            model="mistralai/ministral-3b",
            provider="openrouter",
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

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Router"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    @commands.command(name='router_activate')
    @commands.has_permissions(manage_messages=True)
    async def router_activate(self, ctx):
        """Activate RouterCog for the current channel"""
        channel_id = str(ctx.channel.id)
        RouterCog.active_channels[channel_id] = True
        await ctx.send("✅ Bot will now respond to every message in this channel.")
        logging.info(f"[Router] Activated in channel {channel_id}")

    @commands.command(name='router_deactivate')
    @commands.has_permissions(manage_messages=True)
    async def router_deactivate(self, ctx):
        """Deactivate RouterCog for the current channel"""
        channel_id = str(ctx.channel.id)
        RouterCog.active_channels.pop(channel_id, None)
        await ctx.send("❌ Bot will no longer respond to messages in this channel.")
        logging.info(f"[Router] Deactivated in channel {channel_id}")

    async def handle_message(self, message, full_content=None):
        """Handle incoming messages for routing"""
        try:
            # Skip if message is from this bot
            if message.author == self.bot.user:
                return

            # Skip if message is a command
            if message.content.startswith('!'):
                return

            # Check if channel is active or is a DM
            channel_id = str(message.channel.id)
            if not isinstance(message.channel, discord.DMChannel) and channel_id not in RouterCog.active_channels:
                return

            # Use full_content if provided, otherwise use message content
            content = full_content or message.content

            # Generate response stream
            response_stream = await self.generate_response(message)

            if response_stream:
                # Send response as a stream
                response_message = await message.reply(f"[Router] Processing...")
                full_response = ""
                async for chunk in response_stream:
                    if chunk:
                        full_response += chunk
                        # Update message with current response
                        await response_message.edit(content=f"[Router] {full_response}")

                # Final edit to remove processing indicator
                await response_message.edit(content=f"[Router] {full_response}")
            else:
                await message.reply("[Router] Unable to generate a response.")

        except Exception as e:
            logging.error(f"[Router] Error in handle_message: {e}")
            await message.reply(f"[Router] An error occurred: {str(e)}")

    async def generate_response(self, message):
        """Generate a response using openrouter"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database, excluding current message
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(
                channel_id,
                limit=50,
                exclude_message_id=str(message.id)
            )

            # Format history messages with proper roles
            for msg in history_messages:
                role = "assistant" if msg['is_assistant'] else "user"
                content = msg['content']

                # Handle system summaries
                if msg['user_id'] == 'SYSTEM' and content.startswith('[SUMMARY]'):
                    role = "system"
                    content = content[9:].strip()  # Remove [SUMMARY] prefix

                messages.append({
                    "role": role,
                    "content": content
                })

            # Add the current message
            messages.append({
                "role": "user",
                "content": message.content
            })

            logging.debug(f"[Router] Sending {len(messages)} messages to API")
            logging.debug(f"[Router] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Router] Using temperature: {temperature}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True,
                provider="openpipe",
                user_id=user_id,
                guild_id=guild_id,
                prompt_file="router"
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for Router: {e}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and route them"""
        # Skip if message is from this bot
        if message.author == self.bot.user:
            return

        # Skip if message is a command
        if message.content.startswith('!'):
            return

        # Always handle DMs
        if isinstance(message.channel, discord.DMChannel):
            await self.handle_message(message)
            return

        # Check if channel is activated
        channel_id = str(message.channel.id)
        if channel_id in RouterCog.active_channels:
            await self.handle_message(message)

async def setup(bot):
    try:
        cog = RouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Router] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Router] Failed to register cog: {e}", exc_info=True)
        raise
