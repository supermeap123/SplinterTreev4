import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion, store_alt_text

class GrokCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Grok-Beta",
            nickname="Grok",
            trigger_words=['grok', 'grok beta', 'xai'],
            model="x-ai/grok-beta",
            provider="openrouter",
            prompt_file="grok",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Grok-Beta] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Grok-Beta] Using provider: {self.provider}")
        logging.debug(f"[Grok-Beta] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Grok-Beta"

    async def generate_image_description(self, image_url):
        """Generate a description for the given image URL"""
        try:
            logging.info(f"[Grok-Beta] Starting image description generation for URL: {image_url}")
            
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
            
            logging.debug(f"[Grok-Beta] Constructed vision API messages: {messages}")
            logging.info(f"[Grok-Beta] Calling OpenRouter API for vision processing")
            
            # Call API with vision capabilities
            response_data = await self.api_client.call_openrouter(messages, self.model, temperature=0.3)
            logging.debug(f"[Grok-Beta] Received API response: {response_data}")
            
            if response_data and 'choices' in response_data and len(response_data['choices']) > 0:
                description = response_data['choices'][0]['message']['content']
                # Clean up the description - remove any markdown or quotes
                description = description.strip('`"\' ')
                if description.lower().startswith('alt text:'):
                    description = description[8:].strip()
                logging.info(f"[Grok-Beta] Generated alt text: {description[:100]}...")
                return description
            else:
                logging.error("[Grok-Beta] No description generated for image - API response invalid")
                logging.debug(f"[Grok-Beta] Full API response: {response_data}")
                return None
                
        except Exception as e:
            logging.error(f"[Grok-Beta] Error generating image description: {str(e)}", exc_info=True)
            return None

    async def handle_message(self, message):
        """Override handle_message to ensure proper async flow"""
        if message.author == self.bot.user:
            return

        logging.info(f"[Grok-Beta] Handling message from {message.author}: {message.content[:100]}...")
        logging.debug(f"[Grok-Beta] Message has {len(message.attachments)} attachments")

        # Process images first if there are any attachments
        if message.attachments:
            logging.info(f"[Grok-Beta] Found {len(message.attachments)} attachments")
            image_attachments = [
                att for att in message.attachments 
                if att.content_type and att.content_type.startswith('image/')
            ]
            logging.info(f"[Grok-Beta] Found {len(image_attachments)} image attachments")
            
            if image_attachments:
                logging.info("[Grok-Beta] Starting image processing")
                async with message.channel.typing():
                    for attachment in image_attachments:
                        try:
                            logging.debug(f"[Grok-Beta] Processing attachment: {attachment.filename} ({attachment.content_type})")
                            description = await self.generate_image_description(attachment.url)
                            if description:
                                logging.info(f"[Grok-Beta] Generated description for {attachment.filename}")
                                # Store alt text in database
                                success = await store_alt_text(
                                    message_id=str(message.id),
                                    channel_id=str(message.channel.id),
                                    alt_text=description,
                                    attachment_url=attachment.url
                                )
                                if success:
                                    logging.info(f"[Grok-Beta] Successfully stored alt text for {attachment.filename}")
                                    if message.channel.permissions_for(message.guild.me).add_reactions:
                                        await message.add_reaction('🖼️')
                                else:
                                    logging.error(f"[Grok-Beta] Failed to store alt text for {attachment.filename}")
                                    if message.channel.permissions_for(message.guild.me).add_reactions:
                                        await message.add_reaction('⚠️')
                            else:
                                logging.error(f"[Grok-Beta] Failed to generate description for {attachment.filename}")
                                if message.channel.permissions_for(message.guild.me).add_reactions:
                                    await message.add_reaction('❌')
                        except Exception as e:
                            logging.error(f"[Grok-Beta] Error processing image {attachment.filename}: {str(e)}", exc_info=True)
                            if message.channel.permissions_for(message.guild.me).add_reactions:
                                await message.add_reaction('❌')
                            continue

        # Add message to context before processing
        if self.context_cog:
            try:
                channel_id = str(message.channel.id)
                guild_id = str(message.guild.id) if message.guild else None
                user_id = str(message.author.id)
                content = message.content
                is_assistant = False
                persona_name = self.name
                emotion = None

                await self.context_cog.add_message_to_context(
                    channel_id=channel_id,
                    guild_id=guild_id,
                    user_id=user_id,
                    content=content,
                    is_assistant=is_assistant,
                    persona_name=persona_name,
                    emotion=emotion
                )
            except Exception as e:
                logging.error(f"[Grok-Beta] Failed to add message to context: {str(e)}")

        # Continue with normal message processing
        await super().handle_message(message)

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = GrokCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Grok-Beta] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Grok-Beta] Failed to register cog: {str(e)}", exc_info=True)
        raise
