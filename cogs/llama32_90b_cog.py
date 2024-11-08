import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class Llama3290bVisionCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-90B-Vision",
            nickname="Llama Vision",
            trigger_words=['llamavision', 'describe image', 'what is this image', 'llama', 'llama3', 'llama 3', 'llama 3.2', 'llama3.2', '90b', 'llama 90b', 'vision'],
            model="llama-3.2-90b-vision-preview",
            provider="groq",
            prompt_file="llama32_90b",
            supports_vision=True
        )
        logging.debug(f"[Llama-3.2-90B-Vision] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Llama-3.2-90B-Vision] Using provider: {self.provider}")
        logging.debug(f"[Llama-3.2-90B-Vision] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Llama-3.2-90B-Vision] Failed to load temperatures.json: {e}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Llama-3.2-90B-Vision"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def generate_response(self, message):
        """Generate a response using groq"""
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

            logging.debug(f"[Llama-3.2-90B-Vision] Sending {len(messages)} messages to API")
            logging.debug(f"[Llama-3.2-90B-Vision] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Llama-3.2-90B-Vision] Using temperature: {temperature}")

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True,
                provider="groq"
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for Llama-3.2-90B-Vision: {e}")
            return None

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = Llama3290bVisionCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Llama-3.2-90B-Vision] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Llama-3.2-90B-Vision] Failed to register cog: {e}", exc_info=True)
        raise