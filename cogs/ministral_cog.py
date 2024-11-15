import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class MinistralCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Ministral",
            nickname="Ministral",
            trigger_words=['ministral'],
            model="mistralai/ministral-3b",
            provider="openrouter",
            prompt_file="consolidated_prompts",
            supports_vision=False
        )
        logging.debug(f"[Ministral] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Ministral] Using provider: {self.provider}")
        logging.debug(f"[Ministral] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[Ministral] Failed to load temperatures.json: {e}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Ministral"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)
    async def generate_response(self, message):
        """Generate a response using openrouter with fallback handling"""
        try:
            # Format system prompt
            formatted_prompt = self.format_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database, excluding current message
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(
                channel_id, 
                limit=50,
                exclude_message_id=str(message.id)
            )
            
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

            # Add the current message
            messages.append({
                "role": "user",
                "content": message.content
            })

            logging.debug(f"[Ministral] Sending {len(messages)} messages to API")
            logging.debug(f"[Ministral] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[Ministral] Using temperature: {temperature}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Try primary model first
            try:
                response_stream = await self.api_client.call_openpipe(
                    messages=messages,
                    model=self.model,
                    temperature=temperature,
                    stream=True,
                    provider="openrouter",
                    user_id=user_id,
                    guild_id=guild_id,
                    prompt_file="consolidated_prompts"
                )
                if response_stream:
                    return response_stream
            except Exception as e:
                logging.warning(f"Primary model failed: {e}")

            # Try fallback model if available
            fallback_model = ""
            if fallback_model and fallback_model != self.model:
                try:
                    logging.info(f"[Ministral] Trying fallback model: {fallback_model}")
                    response_stream = await self.api_client.call_openpipe(
                        messages=messages,
                        model=fallback_model,
                        temperature=temperature,
                        stream=True,
                        provider="openrouter",
                        user_id=user_id,
                        guild_id=guild_id,
                        prompt_file="consolidated_prompts"
                    )
                    return response_stream
                except Exception as e:
                    logging.error(f"Fallback model failed: {e}")

            return None

        except Exception as e:
            logging.error(f"Error processing message for Ministral: {e}")
            return None
async def setup(bot):
    try:
        cog = MinistralCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Ministral] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Ministral] Failed to register cog: {e}", exc_info=True)
        raise