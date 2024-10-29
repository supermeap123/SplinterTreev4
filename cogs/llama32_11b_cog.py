import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion, store_alt_text
from shared.api import api

class Llama32_11BCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-11B",
            nickname="Llama",
            trigger_words=['llama', 'llama 3', 'llama3'],
            model="meta-llama/llama-3.2-11b-instruct:free",
            provider="openrouter",
            prompt_file="llama32_11b",
            supports_vision=True
        )
        self.api_client = api
        logging.debug(f"[Llama-3.2-11B] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Llama-3.2-11B] Using provider: {self.provider}")
        logging.debug(f"[Llama-3.2-11B] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Llama-3.2-11B"

    async def generate_image_description(self, image_url):
        """Generate a description for the given image URL"""
        try:
            logging.info(f"[Llama-3.2-11B] Starting image description generation for URL: {image_url}")
            
            # Construct messages for vision API with specific prompt for alt text
            messages = [
                {
                    "role": "system",
                    "content": "You are a vision model specialized in providing detailed, accurate, and concise alt text descriptions of images. Focus on the key visual elements, context, and any text present in the image. Your descriptions should be informative yet concise, suitable for screen readers."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please provide a concise but detailed alt text description of this image:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ]
            
            logging.debug(f"[Llama-3.2-11B] Constructed vision API messages: {messages}")
            logging.info(f"[Llama-3.2-11B] Calling OpenRouter API for vision processing")
            
            # Call API with vision capabilities
            response_data = await self.api_client.call_openrouter(messages, self.model, temperature=0.3)
            logging.debug(f"[Llama-3.2-11B] Received API response: {response_data}")
            
            if response_data and 'choices' in response_data and len(response_data['choices']) > 0:
                description = response_data['choices'][0]['message']['content']
                # Clean up the description - remove any markdown or quotes
                description = description.strip('`"\' ')
                if description.lower().startswith('alt text:'):
                    description = description[8:].strip()
                logging.info(f"[Llama-3.2-11B] Generated alt text: {description[:100]}...")
                return description
            else:
                logging.error("[Llama-3.2-11B] No description generated for image - API response invalid")
                logging.debug(f"[Llama-3.2-11B] Full API response: {response_data}")
                return None
                
        except Exception as e:
            logging.error(f"[Llama-3.2-11B] Error generating image description: {str(e)}", exc_info=True)
            return None

    async def handle_message(self, message):
        """Override handle_message to ensure proper async flow"""
        if message.author == self.bot.user:
            return

        logging.info(f"[Llama-3.2-11B] Handling message from {message.author}: {message.content[:100]}...")
        logging.debug(f"[Llama-3.2-11B] Message has {len(message.attachments)} attachments")

        # Process images first if there are any attachments
        if message.attachments:
            logging.info(f"[Llama-3.2-11B] Found {len(message.attachments)} attachments")
            image_attachments = [
                att for att in message.attachments 
                if att.content_type and att.content_type.startswith('image/')
            ]
            logging.info(f"[Llama-3.2-11B] Found {len(image_attachments)} image attachments")
            
            if image_attachments:
                logging.info("[Llama-3.2-11B] Starting image processing")
                async with message.channel.typing():
                    for attachment in image_attachments:
                        try:
                            logging.debug(f"[Llama-3.2-11B] Processing attachment: {attachment.filename} ({attachment.content_type})")
                            description = await self.generate_image_description(attachment.url)
                            if description:
                                logging.info(f"[Llama-3.2-11B] Generated description for {attachment.filename}")
                                # Store alt text in database
                                success = await store_alt_text(
                                    message_id=str(message.id),
                                    channel_id=str(message.channel.id),
                                    alt_text=description,
                                    attachment_url=attachment.url
                                )
                                if success:
                                    logging.info(f"[Llama-3.2-11B] Successfully stored alt text for {attachment.filename}")
                                    if message.channel.permissions_for(message.guild.me).add_reactions:
                                        await message.add_reaction('🖼️')
                                else:
                                    logging.error(f"[Llama-3.2-11B] Failed to store alt text for {attachment.filename}")
                                    if message.channel.permissions_for(message.guild.me).add_reactions:
                                        await message.add_reaction('⚠️')
                            else:
                                logging.error(f"[Llama-3.2-11B] Failed to generate description for {attachment.filename}")
                                if message.channel.permissions_for(message.guild.me).add_reactions:
                                    await message.add_reaction('❌')
                        except Exception as e:
                            logging.error(f"[Llama-3.2-11B] Error processing image {attachment.filename}: {str(e)}", exc_info=True)
                            if message.channel.permissions_for(message.guild.me).add_reactions:
                                await message.add_reaction('❌')
                            continue

        # Continue with normal message processing
        logging.info("[Llama-3.2-11B] Proceeding with normal message processing")
        await super().handle_message(message)

async def setup(bot):
    """Register the cog with its proper name"""
    try:
        cog = Llama32_11BCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Llama-3.2-11B] Registered cog with name: {cog.name}")
        return cog
    except Exception as e:
        logging.error(f"[Llama-3.2-11B] Failed to register cog: {str(e)}", exc_info=True)
        raise
