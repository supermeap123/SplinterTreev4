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
from typing import Optional, Dict

# Shared cache for image descriptions across all cogs
image_description_cache: Dict[str, str] = {}

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
        
        # Get API client from bot instance
        self.api_client = getattr(bot, 'api_client', None)
        if not self.api_client:
            logging.error(f"[{name}] No API client found on bot")
            raise ValueError("Bot must have api_client attribute")

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

    async def get_image_description(self, image_url: str) -> Optional[str]:
        """Get or generate a description for an image URL"""
        # Check cache first
        if image_url in image_description_cache:
            return image_description_cache[image_url]

        # If this is a vision-capable model, generate the description
        if self.supports_vision and self.name == "Llama-3.2-90B-Vision":
            try:
                async with self._image_processing_lock:
                    response = await self.api_client.call_openrouter(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert at describing images accurately and concisely. Focus on the main subjects and important details."
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": image_url
                                    },
                                    {
                                        "type": "text",
                                        "text": "Please describe this image in detail."
                                    }
                                ]
                            }
                        ],
                        temperature=0.7,
                        stream=False
                    )
                
                if response and response['choices']:
                    description = response['choices'][0]['message']['content'].strip()
                    # Cache the description
                    image_description_cache[image_url] = description
                    return description
            except Exception as e:
                logging.error(f"[{self.name}] Error generating image description: {str(e)}")
        
        return None

    async def handle_message(self, message):
        """Handle incoming messages and generate responses"""
        try:
            # Add message to context
            if self.context_cog:
                try:
                    guild_id = str(message.guild.id) if message.guild else None
                    await self.context_cog.add_message_to_context(
                        message.id,
                        str(message.channel.id),
                        guild_id,
                        str(message.author.id),
                        message.content,
                        False,  # is_assistant
                        None,   # persona_name
                        None    # emotion
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

                # Add response to context
                if self.context_cog:
                    try:
                        guild_id = str(message.guild.id) if message.guild else None
                        await self.context_cog.add_message_to_context(
                            sent_message.id,
                            str(message.channel.id),
                            guild_id,
                            str(self.bot.user.id),
                            response,
                            True,  # is_assistant
                            self.name,  # persona_name
                            emotion  # emotion
                        )
                    except Exception as e:
                        logging.error(f"[{self.name}] Failed to add response to context: {str(e)}")

                # Log interaction
                try:
                    await log_interaction(
                        user_id=message.author.id,
                        guild_id=message.guild.id if message.guild else None,
                        persona_name=self.name,
                        user_message=message.content,
                        assistant_reply=response,
                        emotion=emotion,
                        channel_id=message.channel.id
                    )
                except Exception as e:
                    logging.error(f"[{self.name}] Failed to log interaction: {e}")

        except Exception as e:
            logging.error(f"[{self.name}] Error handling message: {str(e)}")
            await message.channel.send(f"❌ Error: {str(e)}")

    async def generate_response(self, message):
        """Generate a response to a message. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement generate_response")

    def format_prompt(self, message):
        """Format the system prompt template with message context"""
        try:
            tz = ZoneInfo("America/Los_Angeles")
            current_time = datetime.now(tz).strftime("%I:%M %p")
            
            return self.raw_prompt.format(
                MODEL_ID=self.name,
                USERNAME=message.author.display_name,
                DISCORD_USER_ID=message.author.id,
                TIME=current_time,
                TZ="Pacific Time",
                SERVER_NAME=message.guild.name if message.guild else "Direct Message",
                CHANNEL_NAME=message.channel.name if hasattr(message.channel, 'name') else "DM"
            )
        except Exception as e:
            logging.error(f"[{self.name}] Error formatting prompt: {str(e)}")
            return self.raw_prompt

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that might trigger this cog"""
        # Ignore messages from bots
        if message.author.bot:
            return

        # Check if message contains any trigger words
        msg_content = message.content.lower()
        if any(word in msg_content for word in self.trigger_words):
            await self.handle_message(message)
