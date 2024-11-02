import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion, get_message_history
import time
from datetime import datetime
from zoneinfo import ZoneInfo

class Llama32_3B_Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Llama32_3B",
            nickname="Llama3B",
            trigger_words=['llama3b'],
            model="meta-llama/llama-3.2-3b-instruct:free",
            provider="openrouter",
            prompt_file="consolidated_prompts",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[{self.name}] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[{self.name}] Using provider: {self.provider}")
        logging.debug(f"[{self.name}] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return self.name

    async def generate_response(self, message):
        """Generate a response using OpenRouter"""
        try:
            # Format context variables
            tz = ZoneInfo("America/Los_Angeles")
            current_time = datetime.now(tz).strftime("%I:%M %p")
            context = {
                "MODEL_ID": self.name,
                "USERNAME": message.author.display_name,
                "DISCORD_USER_ID": message.author.id,
                "TIME": current_time,
                "TZ": "Pacific Time",
                "SERVER_NAME": message.guild.name if message.guild else "Direct Message",
                "CHANNEL_NAME": message.channel.name if hasattr(message.channel, 'name') else "DM"
            }

            # Format system prompt with variables and add summarization/filtering instructions
            formatted_prompt = self.format_message_content(self.raw_prompt, context)
            formatted_prompt += "\nYou must analyze the full conversation context and any previous model responses to provide a clear, concise summary or response in 3 sentences or less. Focus on maintaining accuracy while being brief."
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get full message history (50 messages)
            history = await get_message_history(message.channel.id)
            
            if history:
                # Add context about the conversation history
                context_summary = "Here's the relevant conversation history:\n\n"
                for entry in history[-50:]:  # Include last 50 messages for full context
                    role_prefix = "User" if entry["role"] == "user" else "Assistant"
                    context_summary += f"{role_prefix}: {entry['content']}\n"
                
                messages.append({
                    "role": "user",
                    "content": (
                        f"Based on the following conversation history, provide a clear and concise response "
                        f"(maximum 3 sentences) that considers all context and previous responses:\n\n"
                        f"{context_summary}\n\n"
                        f"Current message to address: {message.content}"
                    )
                })
            else:
                # If no history, just process the current message
                messages.append({
                    "role": "user",
                    "content": (
                        f"Please provide a clear and concise response (maximum 3 sentences) "
                        f"to the following message: {message.content}"
                    )
                })

            logging.debug(f"[{self.name}] Sending {len(messages)} messages to API")
            logging.debug(f"[{self.name}] System prompt: {formatted_prompt}")

            # Get temperature from base_cog
            temperature = self.get_temperature()
            logging.debug(f"[{self.name}] Using temperature: {temperature}")

            # Call OpenRouter API and return the stream directly
            response_stream = await self.api_client.call_openrouter(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for {self.name}: {str(e)}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Let base_cog handle message processing
        await super().handle_message(message)

async def setup(bot):
    try:
        cog = Llama32_3B_Cog(bot)
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
        raise
