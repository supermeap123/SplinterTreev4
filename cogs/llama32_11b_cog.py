import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class Llama32_11bCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama-3.2-11b",
            nickname="Llama",
            trigger_words=['llama32', 'llama 32', 'llama'],
            model="meta-llama/llama-3.2-11b-vision-instruct",
            provider="openrouter",
            prompt_file="llama",
            supports_vision=True
        )
        logging.debug(f"[Llama-3.2-11b] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Llama-3.2-11b] Using provider: {self.provider}")
        logging.debug(f"[Llama-3.2-11b] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Llama-3.2-11b] Failed to load temperatures.json: {str(e)}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Llama-3.2-11b"

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

            # Add current message with any image descriptions
            if message.attachments:
                # Get alt text for this message
                alt_text = await self.context_cog.get_alt_text(str(message.id))
                if alt_text:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message.content},
                            {"type": "text", "text": f"Image description: {alt_text}"}
                        ]
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": message.content
                    })
            else:
                messages.append({
                    "role": "user",
                    "content": message.content
                })

            logging.debug(f"[Llama-3.2-11b] Sending {len(messages)} messages to API")
            logging.debug(f"[Llama-3.2-11b] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Llama-3.2-11b] Using temperature: {temperature}")

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for Llama-3.2-11b: {str(e)}")
            return None

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = Llama32_11bCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Llama-3.2-11b] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Llama-3.2-11b] Failed to register cog: {str(e)}", exc_info=True)
        raise