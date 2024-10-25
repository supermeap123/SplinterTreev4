import discord
from discord.ext import commands
import logging
import asyncio
from .base_cog import BaseCog
from shared.api import api
from shared.utils import analyze_emotion

class Llama3211bCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-11B",
            nickname="Vision",
            trigger_words=[
                "analyze image", "describe image", 
                "what's in this image", "what is in this image",
                "what do you see in this image"
            ],
            model="meta-llama/llama-3.2-11b-vision-instruct:free",
            provider="openrouter",
            prompt_file="llama32_11b",
            supports_vision=True
        )
        # Define model fallback chain
        self.model_chain = [
            "meta-llama/llama-3.2-11b-vision-instruct:free",  # Free tier
            "meta-llama/llama-3.2-11b-vision-instruct"                # Base model
        ]
        logging.info(f"[Llama Vision] Initialized with model chain: {self.model_chain}")

    async def handle_response(self, response_text, message, referenced_message=None):
        """Handle the response formatting and sending"""
        if not response_text:
            await message.add_reaction('❌')
            await message.reply(f"[{self.name}] Failed to generate a response. Please try again.")
            return None

        try:
            # Format response with model name
            prefixed_response = f"[{self.name}] {response_text}"
            
            # Send reply in chunks if too long
            if len(prefixed_response) > 2000:
                chunks = [prefixed_response[i:i+1900] for i in range(0, len(prefixed_response), 1900)]
                for chunk in chunks:
                    await message.reply(chunk)
            else:
                await message.reply(prefixed_response)

            # Add success reaction
            await message.add_reaction('✅')  # Checkmark for success

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

    async def try_model(self, messages, model):
        """Try to get a response from a specific model"""
        try:
            logging.debug(f"[Llama Vision] Attempting with model: {model}")
            response_data = await api.call_openrouter(messages, model)
            if response_data and isinstance(response_data, dict) and 'choices' in response_data:
                choices = response_data.get('choices', [])
                if choices and len(choices) > 0:
                    first_choice = choices[0]
                    if isinstance(first_choice, dict) and 'message' in first_choice:
                        content = first_choice['message'].get('content')
                        if content:
                            logging.debug(f"[Llama Vision] Successfully got response from {model}")
                            return content
            return None
        except Exception as e:
            if "rate limit" in str(e).lower():
                logging.warning(f"[Llama Vision] Rate limited on model: {model}")
                raise  # Re-raise to handle in process_message
            else:
                logging.error(f"[Llama Vision] Error with model {model}: {str(e)}")
                return None

    async def process_message(self, message, context=None):
        """Process message with image handling"""
        try:
            # Build messages array with system prompt
            messages = [
                {"role": "system", "content": self.raw_prompt}
            ]
            logging.debug(f"[Llama Vision] Using system prompt: {self.raw_prompt}")

            # Add context if provided
            if context:
                messages.extend(context)
                logging.debug(f"[Llama Vision] Added context: {context}")

            # Process images
            image_content = []
            
            # First check direct attachments
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    logging.debug(f"[Llama Vision] Processing attachment: {attachment.filename}")
                    image_b64 = await self.encode_image_to_base64(attachment.url)
                    if image_b64:
                        image_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }
                        })
                        logging.debug("[Llama Vision] Successfully encoded attachment")

            # If no direct attachments, look for recent images
            if not image_content:
                logging.debug("[Llama Vision] No attachments found, looking for recent images")
                recent_image, source_message = await self.find_recent_image(message)
                if recent_image:
                    logging.debug("[Llama Vision] Found recent image")
                    image_b64 = await self.encode_image_to_base64(recent_image.url)
                    if image_b64:
                        image_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }
                        })
                        logging.debug("[Llama Vision] Successfully encoded recent image")

            if not image_content:
                logging.warning("[Llama Vision] No images found to analyze")
                await message.reply(f"[{self.name}] No image found to analyze. Please provide an image or use this command right after an image is posted.")
                return None

            # Add text and image content
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message.content or "Please describe this image in detail."},
                    *image_content
                ]
            })
            logging.debug(f"[Llama Vision] Final message content: {message.content}")

            # Try each model in the chain until one works
            last_error = None
            for model in self.model_chain:
                try:
                    if response := await self.try_model(messages, model):
                        return response
                except Exception as e:
                    last_error = e
                    if "rate limit" not in str(e).lower():
                        break  # Only continue on rate limit errors
                    logging.info(f"[Llama Vision] Model {model} failed, trying next in chain")
                    continue

            if last_error:
                logging.error(f"[Llama Vision] All models failed. Last error: {str(last_error)}")
            else:
                logging.error("[Llama Vision] All models failed to generate a response")
            return None

        except Exception as e:
            logging.error(f"[Llama Vision] Error processing message: {str(e)}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        msg_content = message.content.lower()
        is_triggered = any(word in msg_content for word in self.trigger_words)

        if is_triggered:
            try:
                logging.debug(f"[Llama Vision] Triggered by message: {message.content}")
                async with message.channel.typing():
                    # Add processing reaction
                    await message.add_reaction('🔍')  # Magnifying glass to show processing
                    
                    # Process message and get response
                    response = await self.process_message(message)
                    
                    # Remove processing reaction
                    try:
                        await message.remove_reaction('🔍', self.bot.user)
                    except:
                        pass
                    
                    if response:
                        await self.handle_response(response, message)
                    else:
                        await message.add_reaction('❌')
                        await message.reply(f"[{self.name}] Failed to analyze the image. Please try again.")

            except Exception as e:
                logging.error(f"[Llama Vision] Error in message handling: {str(e)}")
                try:
                    await message.remove_reaction('🔍', self.bot.user)
                    await message.add_reaction('❌')
                except:
                    pass
                await message.reply(f"[{self.name}] An error occurred while processing your request.")

async def setup(bot):
    await bot.add_cog(Llama3211bCog(bot))
