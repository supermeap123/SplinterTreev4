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
                    history.append({
                        "role": "user",
                        "content": msg.content,
                        "name": msg.author.display_name
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
            response_data = await api.call_openrouter(messages, llama_cog.model)
            
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
            logging.debug(f"[{self.name}] Formatted prompt: {formatted_prompt}")

            # Build messages array with system prompt
            messages = [
                {"role": "system", "content": formatted_prompt}
            ]

            # Get channel history
            context_limit = CONTEXT_WINDOWS.get(str(message.channel.id), DEFAULT_CONTEXT_WINDOW)
            context_limit = min(context_limit, MAX_CONTEXT_WINDOW)
            context = await self.get_channel_history(message, limit=context_limit)
            logging.debug(f"[{self.name}] Using channel history as context: {len(context)} messages")

            # Add context messages
            if context:
                messages.extend(context)
                logging.debug(f"[{self.name}] Added context: {len(context)} messages")

            # Check for images
            has_image = False
            image_description = None
            
            # First check direct attachments
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    has_image = True
                    logging.debug(f"[{self.name}] Found image attachment: {attachment.filename}")
                    if not self.supports_vision:
                        # Get image description for non-vision models
                        image_description = await self.get_image_description(attachment.url)
                        logging.debug(f"[{self.name}] Got image description: {image_description}")
                    break

            # If no direct attachments, look for recent images
            if not has_image:
                recent_image, source_message = await self.find_recent_image(message)
                if recent_image:
                    has_image = True
                    logging.debug(f"[{self.name}] Found recent image")
                    if not self.supports_vision:
                        # Get image description for non-vision models
                        image_description = await self.get_image_description(recent_image.url)
                        logging.debug(f"[{self.name}] Got image description: {image_description}")

            # Add message content
            if has_image:
                if self.supports_vision:
                    # For vision models, add image directly
                    image_content = []
                    if message.attachments:
                        for attachment in message.attachments:
                            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                image_b64 = await self.encode_image_to_base64(attachment.url)
                                if image_b64:
                                    image_content.append({
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_b64}",
                                            "detail": "high"
                                        }
                                    })
                    else:
                        recent_image, _ = await self.find_recent_image(message)
                        if recent_image:
                            image_b64 = await self.encode_image_to_base64(recent_image.url)
                            if image_b64:
                                image_content.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}",
                                        "detail": "high"
                                    }
                                })

                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message.content},
                            *image_content
                        ]
                    })
                    logging.debug(f"[{self.name}] Added vision content to message")
                else:
                    # For non-vision models, add image description as context
                    if image_description:
                        messages.append({
                            "role": "system",
                            "content": f"The following message refers to an image. Here is a detailed description of the image: {image_description}"
                        })
                        logging.debug(f"[{self.name}] Added image description to context")
                    messages.append({
                        "role": "user",
                        "content": message.content
                    })
            else:
                messages.append({
                    "role": "user",
                    "content": message.content
                })

            logging.debug(f"[{self.name}] Final messages array: {messages}")

            # Call API based on provider
            if self.provider == "openrouter":
                response_data = await api.call_openrouter(messages, self.model)
            else:  # openpipe
                response_data = await api.call_openpipe(messages, self.model)

            if response_data and 'choices' in response_data and len(response_data['choices']) > 0:
                response = response_data['choices'][0]['message']['content']
                logging.debug(f"[{self.name}] Got response: {response}")
                return response

            logging.warning(f"[{self.name}] No valid response received from API")
            return None

        except Exception as e:
            logging.error(f"Error processing message for {self.name}: {str(e)}")
            return None
