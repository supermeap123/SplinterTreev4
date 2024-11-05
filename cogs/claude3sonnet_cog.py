import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class Claude3SonnetCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-3-Sonnet",
            nickname="Sonnet",
            trigger_words=['claude3sonnet', 'sonnet', 'claude 3 sonnet'],
            model="anthropic/claude-3.5-sonnet:beta",
            provider="openrouter",
            prompt_file="claude",
            supports_vision=True
        )
        logging.debug(f"[Claude-3-Sonnet] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Claude-3-Sonnet] Using provider: {self.provider}")
        logging.debug(f"[Claude-3-Sonnet] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Claude-3-Sonnet] Failed to load temperatures.json: {e}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Claude-3-Sonnet"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def generate_response(self, message):
        """Generate a response using openrouter"""
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
                    if self.is_valid_image_url(attachment.url):
                        content.append({
                            "type": "image_url",
                            "image_url": attachment.url
                        })

            # Check for image URLs in embeds
            for embed in message.embeds:
                if embed.image and embed.image.url and self.is_valid_image_url(embed.image.url):
                    content.append({
                        "type": "image_url",
                        "image_url": embed.image.url
                    })
                if embed.thumbnail and embed.thumbnail.url and self.is_valid_image_url(embed.thumbnail.url):
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

            logging.debug(f"[Claude-3-Sonnet] Sending {len(messages)} messages to API")
            logging.debug(f"[Claude-3-Sonnet] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Claude-3-Sonnet] Using temperature: {temperature}")

            # Call API and stream the response
            return await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True
            )

        except Exception as e:
            logging.error(f"Error processing message for Claude-3-Sonnet: {e}")
            return None

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = Claude3SonnetCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Claude-3-Sonnet] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-3-Sonnet] Failed to register cog: {e}", exc_info=True)
        raise
