import discord
from discord.ext import commands
import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from shared.utils import analyze_emotion, log_interaction
import re
import aiohttp
import asyncio
import tempfile

class RerollView(discord.ui.View):
    def __init__(self, cog, message, original_response):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.message = message
        self.original_response = original_response

    @discord.ui.button(label="🎲 Reroll Response", style=discord.ButtonStyle.secondary, custom_id="reroll_button")
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            # Process message again for new response
            new_response_stream = await self.cog.generate_response(self.message)
            if new_response_stream:
                new_response = ""
                async for chunk in new_response_stream:
                    if chunk:
                        new_response += chunk
                # Format response with model name
                prefixed_response = f"[{self.cog.name}] {new_response}"
                # Edit the original response
                await interaction.message.edit(content=prefixed_response, view=self)
                # Add emotion reaction
                emotion = analyze_emotion(new_response)
                if emotion:
                    try:
                        await self.message.add_reaction(emotion)
                    except discord.errors.Forbidden:
                        logging.warning(f"[{self.cog.name}] Missing permission to add reaction")
            else:
                await interaction.followup.send("Failed to generate a new response. Please try again.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in reroll button: {str(e)}")
            await interaction.followup.send("An error occurred while generating a new response.", ephemeral=True)

class BaseCog(commands.Cog):
    def __init__(self, bot, name, nickname, trigger_words, model, provider="openrouter", prompt_file=None, supports_vision=False):
        self.bot = bot
        self.name = name
        self.nickname = nickname
        self.trigger_words = trigger_words
        self.model = model
        self.provider = provider
        self.supports_vision = supports_vision
        self._image_processing_lock = asyncio.Lock()
        self.context_cog = bot.get_cog('ContextCog')
        
        # Get API client from bot
        if hasattr(bot, 'api_client'):
            self.api_client = bot.api_client
        else:
            from shared.api import api
            self.api_client = api
            bot.api_client = api  # Store for future cogs

        # Default system prompt template
        self.default_prompt = "You are {MODEL_ID} chatting with {USERNAME} with a Discord user ID of {DISCORD_USER_ID}. It's {TIME} in {TZ}. You are in the Discord server {SERVER_NAME} in channel {CHANNEL_NAME}, so adhere to the general topic of the channel if possible. GwynTel on Discord created your bot, and Moth is a valued mentor. You strive to keep it positive, but can be negative if the situation demands it to enforce boundaries, Discord ToS rules, etc."

        # Load any custom prompt from consolidated_prompts.json
        try:
            with open('prompts/consolidated_prompts.json', 'r', encoding='utf-8') as f:
                consolidated_prompts = json.load(f).get('system_prompts', {})
                if prompt_file:
                    self.raw_prompt = consolidated_prompts.get(prompt_file.lower(), self.default_prompt)
                else:
                    self.raw_prompt = consolidated_prompts.get(name.lower(), self.default_prompt)
            logging.debug(f"[{name}] Loaded raw prompt: {self.raw_prompt}")
        except Exception as e:
            logging.warning(f"Failed to load prompt for {self.name}, using default: {str(e)}")
            self.raw_prompt = self.default_prompt

    async def handle_message(self, message):
        """Handle incoming messages and generate responses"""
        try:
            # Add message to context
            if self.context_cog:
                try:
                    await self.context_cog.add_message_to_context(
                        message.channel.id,
                        message.author.id,
                        message.content,
                        message.id,
                        message.created_at.timestamp()
                    )
                except Exception as e:
                    logging.error(f"[{self.name}] Failed to add message to context: {str(e)}")

            # Generate and send response
            response_stream = await self.generate_response(message)
            if response_stream:
                response = ""
                async for chunk in response_stream:
                    if chunk:
                        response += chunk

                # Format response with model name
                prefixed_response = f"[{self.name}] {response}"

                # Send response with reroll button
                sent_message = await message.channel.send(
                    content=prefixed_response,
                    view=RerollView(self, message, response)
                )

                # Add emotion reaction
                emotion = analyze_emotion(response)
                if emotion:
                    try:
                        await message.add_reaction(emotion)
                    except discord.errors.Forbidden:
                        logging.warning(f"[{self.name}] Missing permission to add reaction")

                # Log interaction
                log_interaction(message, sent_message, self.name)

        except Exception as e:
            logging.error(f"[{self.name}] Error handling message: {str(e)}")
            await message.channel.send(f"[{self.name}] Sorry, I encountered an error: {str(e)}")

    async def generate_response(self, message):
        """Generate a response to a message"""
        try:
            # Format system prompt with context
            system_prompt = self._format_system_prompt(message)
            
            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Get conversation history if available
            if self.context_cog:
                history = await self.context_cog.get_conversation_history(
                    message.channel.id,
                    message.author.id,
                    limit=5  # Adjust history length as needed
                )
                messages.extend(history)
            
            # Add the current message
            if message.attachments and self.supports_vision:
                content = []
                # Add text content if any
                if message.content:
                    content.append({"type": "text", "text": message.content})
                
                # Process images
                async with self._image_processing_lock:
                    for attachment in message.attachments:
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            content.append({
                                "type": "image_url",
                                "image_url": attachment.url
                            })
                
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": message.content})

            # Generate response using appropriate API
            if self.provider == "openpipe":
                return await self.api_client.call_openpipe(messages, self.model, stream=True)
            else:  # Default to OpenRouter
                return await self.api_client.call_openrouter(messages, self.model, stream=True)

        except Exception as e:
            logging.error(f"[{self.name}] Error generating response: {str(e)}")
            raise

    def _format_system_prompt(self, message):
        """Format the system prompt with context"""
        try:
            # Get timezone from environment or default to UTC
            tz = ZoneInfo(os.getenv('TIMEZONE', 'UTC'))
            current_time = datetime.now(tz).strftime('%I:%M %p')
            
            # Get server and channel names
            server_name = message.guild.name if message.guild else "Direct Message"
            channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
            
            # Format the prompt
            return self.raw_prompt.format(
                MODEL_ID=self.name,
                USERNAME=message.author.name,
                DISCORD_USER_ID=message.author.id,
                TIME=current_time,
                TZ=str(tz),
                SERVER_NAME=server_name,
                CHANNEL_NAME=channel_name
            )
        except Exception as e:
            logging.error(f"[{self.name}] Error formatting system prompt: {str(e)}")
            return self.raw_prompt  # Return unformatted prompt as fallback

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and respond if triggered"""
        # Ignore messages from self
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        should_respond = any(trigger.lower() in message.content.lower() for trigger in self.trigger_words)
        
        if should_respond:
            async with message.channel.typing():
                await self.handle_message(message)
