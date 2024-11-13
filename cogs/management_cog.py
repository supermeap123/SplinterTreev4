import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json
import os

class ManagementCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Management",
            nickname="Management",
            trigger_words=[],
            model="meta-llama/llama-3.1-405b-instruct",
            provider="openrouter",
            prompt_file="None",
            supports_vision=False
        )
        logging.debug(f"[Management] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Management] Using provider: {self.provider}")
        logging.debug(f"[Management] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Management] Failed to load temperatures.json: {e}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Management"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    def save_activated_channels(self, activated_channels):
        """Save activated channels to JSON file"""
        try:
            with open('activated_channels.json', 'w') as f:
                json.dump(activated_channels, f, indent=2)
            logging.info(f"[Management] Saved activated channels: {activated_channels}")
        except Exception as e:
            logging.error(f"[Management] Failed to save activated channels: {e}")

    @commands.command(name='st_activate')
    @commands.has_permissions(manage_messages=True)
    async def st_activate_channel(self, ctx):
        """Activate the bot in the current channel"""
        try:
            # Load current activated channels
            activated_channels = {}
            if os.path.exists('activated_channels.json'):
                with open('activated_channels.json', 'r') as f:
                    activated_channels = json.load(f)

            guild_id = str(ctx.guild.id)
            channel_id = str(ctx.channel.id)

            # Initialize guild entry if it doesn't exist
            if guild_id not in activated_channels:
                activated_channels[guild_id] = []

            # Add channel if not already activated
            if channel_id not in activated_channels[guild_id]:
                activated_channels[guild_id].append(channel_id)
                self.save_activated_channels(activated_channels)

                # Update RouterCog's activated_channels
                router_cog = self.bot.get_cog('RouterCog')
                if router_cog:
                    router_cog.activated_channels = activated_channels

                await ctx.send("✅ Bot will now respond to every message in this channel.")
            else:
                await ctx.send("ℹ️ Bot is already activated in this channel.")

        except Exception as e:
            logging.error(f"[Management] Error activating channel: {e}")
            await ctx.send("❌ Failed to activate bot in this channel.")

    @commands.command(name='st_deactivate')
    @commands.has_permissions(manage_messages=True)
    async def st_deactivate_channel(self, ctx):
        """Deactivate the bot in the current channel"""
        try:
            # Load current activated channels
            activated_channels = {}
            if os.path.exists('activated_channels.json'):
                with open('activated_channels.json', 'r') as f:
                    activated_channels = json.load(f)

            guild_id = str(ctx.guild.id)
            channel_id = str(ctx.channel.id)

            # Remove channel if activated
            if guild_id in activated_channels and channel_id in activated_channels[guild_id]:
                activated_channels[guild_id].remove(channel_id)
                
                # Remove guild entry if no channels left
                if not activated_channels[guild_id]:
                    del activated_channels[guild_id]

                self.save_activated_channels(activated_channels)

                # Update RouterCog's activated_channels
                router_cog = self.bot.get_cog('RouterCog')
                if router_cog:
                    router_cog.activated_channels = activated_channels

                await ctx.send("✅ Bot will no longer respond to every message in this channel.")
            else:
                await ctx.send("ℹ️ Bot is not activated in this channel.")

        except Exception as e:
            logging.error(f"[Management] Error deactivating channel: {e}")
            await ctx.send("❌ Failed to deactivate bot in this channel.")

    @commands.command(name='st_listactive')
    @commands.has_permissions(manage_messages=True)
    async def st_list_active_channels(self, ctx):
        """List all activated channels in the current guild"""
        try:
            # Load current activated channels
            activated_channels = {}
            if os.path.exists('activated_channels.json'):
                with open('activated_channels.json', 'r') as f:
                    activated_channels = json.load(f)

            guild_id = str(ctx.guild.id)

            if guild_id in activated_channels and activated_channels[guild_id]:
                channels = []
                for channel_id in activated_channels[guild_id]:
                    channel = ctx.guild.get_channel(int(channel_id))
                    if channel:
                        channels.append(f"#{channel.name}")

                if channels:
                    await ctx.send(f"🔍 Active channels in this server:\n{', '.join(channels)}")
                else:
                    await ctx.send("ℹ️ No active channels found in this server.")
            else:
                await ctx.send("ℹ️ No active channels found in this server.")

        except Exception as e:
            logging.error(f"[Management] Error listing active channels: {e}")
            await ctx.send("❌ Failed to list active channels.")

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

            # Process current message and any images
            content = []
            has_images = False
            
            # Add any image attachments
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": attachment.url }
                    })

            # Check for image URLs in embeds
            for embed in message.embeds:
                if embed.image and embed.image.url:
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": embed.image.url }
                    })
                if embed.thumbnail and embed.thumbnail.url:
                    has_images = True
                    content.append({
                        "type": "image_url",
                        "image_url": { "url": embed.thumbnail.url }
                    })

            # Add the text content
            content.append({
                "type": "text",
                "text": "Please describe this image in detail." if has_images else message.content
            })

            # Add the message with multimodal content
            messages.append({
                "role": "user",
                "content": content
            })

            logging.debug(f"[Management] Sending {len(messages)} messages to API")
            logging.debug(f"[Management] Formatted prompt: {formatted_prompt}")
            logging.debug(f"[Management] Has images: {has_images}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Management] Using temperature: {temperature}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True,
                provider="openrouter",
                user_id=user_id,
                guild_id=guild_id,
                prompt_file="None"
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for Management: {e}")
            return None

async def setup(bot):
    try:
        cog = ManagementCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Management] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Management] Failed to register cog: {e}", exc_info=True)
        raise
