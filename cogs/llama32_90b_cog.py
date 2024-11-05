import discord
from discord.ext import commands
import logging
from typing import Optional
from .base_cog import BaseCog
import json

class Llama3290bVisionCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-90B-Vision",
            nickname="Llama Vision",
            trigger_words=['llamavision', 'describe image', 'what is this image', 'llama', 'llama3', 'llama 3', 'llama 3.2', 'llama3.2', '90b', 'llama 90b', 'vision'],
            model="meta-llama/llama-3.2-90b-vision-instruct:free",
            provider="openrouter",
            prompt_file="llama32_90b",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[{self.name}] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[{self.name}] Using provider: {self.provider}")
        logging.debug(f"[{self.name}] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[{self.name}] Failed to load temperatures.json: {e}")
            self.temperatures = {}

    async def generate_response(self, message):
        """Generate a response using the vision model"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(channel_id, limit=50)
            
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
            
            # Add any image attachments
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    content.append({
                        "type": "image_url",
                        "image_url": attachment.url
                    })

            # Check for image URLs in embeds
            for embed in message.embeds:
                if embed.image and embed.image.url:
                    content.append({
                        "type": "image_url",
                        "image_url": embed.image.url
                    })
                if embed.thumbnail and embed.thumbnail.url:
                    content.append({
                        "type": "image_url",
                        "image_url": embed.thumbnail.url
                    })

            # Add the text content
            content.append({
                "type": "text",
                "text": message.content
            })

            # Add the message with multimodal content
            messages.append({
                "role": "user",
                "content": content if len(content) > 1 else message.content
            })

            logging.debug(f"[{self.name}] Sending {len(messages)} messages to API")
            logging.debug(f"[{self.name}] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[{self.name}] Using temperature: {temperature}")

            # Call API and stream the response
            async for chunk in await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True
            ):
                yield chunk

        except Exception as e:
            logging.error(f"Error processing message for {self.name}: {e}")
            yield f"❌ Error: {str(e)}"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

async def setup(bot):
    await bot.add_cog(Llama3290bVisionCog(bot))
