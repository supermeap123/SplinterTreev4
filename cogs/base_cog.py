import discord
from discord.ext import commands
import json
import logging
import random
import os
import base64
import aiohttp
import io
import re
from datetime import datetime
from shared.utils import analyze_emotion
from shared.api import api, time
from config import (
    DEFAULT_CONTEXT_WINDOW, 
    MAX_CONTEXT_WINDOW, 
    CONTEXT_WINDOWS,
    SHARED_HISTORY_ENABLED,
    IMAGE_PROCESSING_ENABLED
)

class RerollView(discord.ui.View):
    def __init__(self, cog, message, original_response):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.message = message
        self.original_response = original_response

    @discord.ui.button(label="🎲 Reroll Response", style=discord.ButtonStyle.secondary)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            async with interaction.channel.typing():
                # Process message again for new response
                new_response = await self.cog.process_message(self.message)
                if new_response:
                    # Format response with model name
                    prefixed_response = f"[{self.cog.name}] {new_response}"
                    
                    # Edit the original response
                    await interaction.message.edit(content=prefixed_response, view=self)
                    
                    # Add emotion reaction
                    emotion = analyze_emotion(new_response)
                    if emotion:
                        await interaction.message.add_reaction(emotion)
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

        # Load prompt
        try:
            with open('prompts/consolidated_prompts.json', 'r', encoding='utf-8') as f:
                consolidated_prompts = json.load(f).get('system_prompts', {})
                if prompt_file:
                    raw_prompt = consolidated_prompts.get(prompt_file.lower(), f"You are {name}, an advanced AI assistant focused on providing accurate and helpful responses.")
                else:
                    raw_prompt = consolidated_prompts.get(name.lower(), f"You are {name}, an advanced AI assistant focused on providing accurate and helpful responses.")
            logging.debug(f"[{name}] Loaded raw prompt: {raw_prompt}")
        except Exception as e:
            logging.warning(f"Failed to load prompt for {self.name}, using default: {str(e)}")
            raw_prompt = f"You are {name}, an advanced AI assistant focused on providing accurate and helpful responses."

        # Assign the raw prompt; substitution will occur in process_message
        self.raw_prompt = raw_prompt
        self.formatted_prompt = raw_prompt

    def sanitize_username(self, username: str) -> str:
        """Sanitize username to match the pattern ^[a-zA-Z0-9_-]+$"""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\-]', '_', username)
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized

    def get_dynamic_prompt(self, ctx):
        """Get dynamic prompt for channel/server if one exists"""
        guild_id = str(ctx.guild.id) if ctx.guild else None
        channel_id = str(ctx.channel.id)

        prompts_file = "dynamic_prompts.json"
        if not os.path.exists(prompts_file):
            return None

        try:
            with open(prompts_file, "r") as f:
                dynamic_prompts = json.load(f)

            if guild_id in dynamic_prompts and channel_id in dynamic_prompts[guild_id]:
                return dynamic_prompts[guild_id][channel_id]
            elif channel_id in dynamic_prompts:
                return dynamic_prompts[channel_id]
            else:
                return None
        except Exception as e:
            logging.error(f"Error getting dynamic prompt: {str(e)}")
            return None

    def get_temperature(self, agent_name):
        """Get temperature for agent if one exists"""
        temperatures_file = "temperatures.json"
        if not os.path.exists(temperatures_file):
            return None  # Let API use default temperature

        try:
            with open(temperatures_file, "r") as f:
                temperatures = json.load(f)
            return temperatures.get(agent_name)  # Return None if not found
        except Exception as e:
            logging.error(f"Error getting temperature: {str(e)}")
            return None

    async def get_channel_history(self, message, limit: int = None) -> list:
        """Get message history for a channel directly from Discord"""
        try:
            if not SHARED_HISTORY_ENABLED:
                logging.debug(f"[{self.name}] Shared history is disabled. Returning empty context.")
                return []

            if not limit:
                limit = CONTEXT_WINDOWS.get(str(message.channel.id), DEFAULT_CONTEXT_WINDOW)
            else:
                limit = min(limit, MAX_CONTEXT_WINDOW)

            history = []
            async for msg in message.channel.history(limit=limit, oldest_first=False):
                if msg.author == self.bot.user:
                    # Extract model name from bot responses
                    content = msg.content
                    if content.startswith('['):
                        content = content[content.find(']')+1:].strip()
                    history.append({
                        "role": "assistant",
                        "content": content
                    })
                else:
                    # Add sanitized username for user messages
                    sanitized_name = self.sanitize_username(msg.author.display_name)
                    history.append({
                        "role": "user",
                        "content": msg.content,
                        "name": sanitized_name
                    })

            history.reverse()  # Ensure the messages are in chronological order
            logging.debug(f"[{self.name}] Retrieved {len(history)} messages from channel history for channel {message.channel.id}")
            return history
        except Exception as e:
            logging.error(f"Error getting channel history: {str(e)}")
            return []

    async def update_context_window(self, channel_id: str, size: int):
        """Update the context window size for a specific channel"""
        try:
            if size < 1 or size > MAX_CONTEXT_WINDOW:
                logging.warning(f"[{self.name}] Invalid context window size: {size}. Using default.")
                size = DEFAULT_CONTEXT_WINDOW
            CONTEXT_WINDOWS[channel_id] = size
            logging.info(f"[{self.name}] Updated context window size for channel {channel_id} to {size}")
        except Exception as e:
            logging.error(f"Error updating context window size: {str(e)}")

    async def encode_image_to_base64(self, image_url):
        """Convert image to base64 encoding"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return base64.b64encode(image_data).decode('utf-8')
            return None
        except Exception as e:
            logging.error(f"Error encoding image: {str(e)}")
            return None

    async def find_recent_image(self, message, limit=10):
        """Find the most recent image in the channel"""
        try:
            async for msg in message.channel.history(limit=limit):
                # Check message attachments
                for attachment in msg.attachments:
                    if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        logging.debug(f"[{self.name}] Found recent image in attachment: {attachment.filename}")
                        return attachment, msg

                # Check message embeds
                for embed in msg.embeds:
                    if embed.image:
                        logging.debug(f"[{self.name}] Found recent image in embed")
                        return embed.image, msg
            return None, None
        except Exception as e:
            logging.error(f"Error finding recent image: {str(e)}")
            return None, None

    async def get_image_description(self, image_url):
        """Get image description using Llama vision model"""
        if not IMAGE_PROCESSING_ENABLED:
            logging.debug(f"[{self.name}] Image processing is disabled. Skipping image description.")
            return None

        try:
            # Find Llama cog
            llama_cog = None
            for cog in self.bot.cogs.values():
                if isinstance(cog, commands.Cog) and getattr(cog, 'name', '') == 'Llama-3.2-11B':
                    llama_cog = cog
                    break

            if not llama_cog:
                logging.error("Llama vision cog not found")
                return None

            logging.debug(f"[{self.name}] Found Llama cog for image description")

            # Encode image
            image_b64 = await self.encode_image_to_base64(image_url)
            if not image_b64:
                return None

            # Build messages for vision analysis
            messages = [
                {"role": "system", "content": llama_cog.raw_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please provide a detailed description of this image that can be used as context for other AI models."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]

            logging.debug(f"[{self.name}] Sending image analysis request to Llama")

            # Call API
            response_data = await api.call_openrouter(messages, llama_cog.model, temperature=None)
            
            if response_data and isinstance(response_data, dict) and 'choices' in response_data:
                choices = response_data.get('choices', [])
                if choices and len(choices) > 0:
                    first_choice = choices[0]
                    if isinstance(first_choice, dict) and 'message' in first_choice:
                        description = first_choice['message'].get('content')
                        logging.debug(f"[{self.name}] Got image description: {description}")
                        return description

            return None

        except Exception as e:
            logging.error(f"Error getting image description: {str(e)}")
            return None

    async def handle_response(self, response_text, message, referenced_message=None):
        """Handle the response formatting and sending"""
        try:
            # Format response with model name
            prefixed_response = f"[{self.name}] {response_text}"
            
            # Create reroll view
            view = RerollView(self, message, response_text)
            
            # Send reply in chunks if too long
            if len(prefixed_response) > 2000:
                chunks = [prefixed_response[i:i+1900] for i in range(0, len(prefixed_response), 1900)]
                sent_messages = []
                for i, chunk in enumerate(chunks):
                    # Only add view to last chunk
                    if i == len(chunks) - 1:
                        sent_message = await message.reply(chunk, view=view)
                    else:
                        sent_message = await message.reply(chunk)
                    sent_messages.append(sent_message)
            else:
                sent_message = await message.reply(prefixed_response, view=view)

            # Add reaction based on emotion analysis
            try:
                emotion = analyze_emotion(response_text)
                if emotion:
                    await message.add_reaction(emotion)
            except Exception as e:
                logging.error(f"Error adding emotion reaction: {str(e)}")
            
            return emotion

        except Exception as e:
            logging.error(f"Error sending response for {self.name}: {str(e)}")
            try:
                await message.add_reaction('❌')
            except:
                pass
            return None

    async def process_message(self, message, context=None):
        """Process message and generate response"""
        try:
            # Format system prompt with dynamic variables
            formatted_prompt = self.raw_prompt.format(
                discord_user=message.author.display_name,
                discord_user_id=message.author.id,
                local_time=datetime.now().strftime("%I:%M %p"),
                local_timezone="UTC",  # Could be made dynamic if needed
                server_name=message.guild.name if message.guild else "Direct Message",
                channel_name=message.channel.name if hasattr(message.channel, 'name') else "DM"
            )

            # Get dynamic prompt if one exists
            dynamic_prompt = self.get_dynamic_prompt(message)
            if dynamic_prompt:
                # Add dynamic prompt as a second system message
                messages = [
                    {"role": "system", "content": formatted_prompt},
                    {"role": "system", "content": dynamic_prompt}
                ]
            else:
                messages = [
                    {"role": "system", "content": formatted_prompt}
                ]

            logging.debug(f"[{self.name}] Formatted prompt: {formatted_prompt}")
            if dynamic_prompt:
                logging.debug(f"[{self.name}] Added dynamic prompt: {dynamic_prompt}")

            # Add user message
            messages.append({
                "role": "user",
                "content": message.content
            })

            # Get temperature for this agent
            temperature = self.get_temperature(self.name)
            logging.debug(f"[{self.name}] Using temperature: {temperature}")

            # Call API based on provider with temperature
            if self.provider == "openrouter":
                response_data = await api.call_openrouter(messages, self.model, temperature=temperature)
            else:  # openpipe
                response_data = await api.call_openpipe(messages, self.model, temperature=temperature)

            if response_data and 'choices' in response_data and len(response_data['choices']) > 0:
                response = response_data['choices'][0]['message']['content']
                logging.debug(f"[{self.name}] Got response: {response}")
                return response

            logging.warning(f"[{self.name}] No valid response received from API")
            return None

        except Exception as e:
            logging.error(f"Error processing message for {self.name}: {str(e)}")
            return None
