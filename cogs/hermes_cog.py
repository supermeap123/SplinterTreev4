import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion, get_message_history
import time

class HermesCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Hermes-3",
            nickname="Hermes",
            trigger_words=['hermes'],
            model="nousresearch/hermes-3-llama-3.1-405b:free",
            provider="openrouter",
            prompt_file="hermes",
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
            tz = "Pacific Time"
            current_time = time.strftime("%I:%M %p", time.localtime())
            context = {
                "MODEL_ID": self.name,
                "USERNAME": message.author.display_name,
                "DISCORD_USER_ID": message.author.id,
                "TIME": current_time,
                "TZ": tz,
                "SERVER_NAME": message.guild.name if message.guild else "Direct Message",
                "CHANNEL_NAME": message.channel.name if hasattr(message.channel, 'name') else "DM"
            }

            # Format system prompt with context
            system_prompt = self.raw_prompt.format(**context)
            messages = [{"role": "system", "content": system_prompt}]

            # Get message history
            history = await get_message_history(message.channel.id)
            if history:
                for entry in history[-5:]:  # Include last 5 messages for context
                    content = entry["content"].format(**context)
                    messages.append({"role": entry["role"], "content": content})

            # Add current message
            messages.append({
                "role": "user",
                "content": message.content
            })

            logging.debug(f"[{self.name}] Sending {len(messages)} messages to API")
            logging.debug(f"[{self.name}] System prompt: {system_prompt}")

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
        logging.info(f"[Hermes-3] Starting cog setup...")
        cog = HermesCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[{cog.name}] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[{cog.name}] Cog is loaded and listening for triggers: {cog.trigger_words}")
        return cog
    except Exception as e:
        logging.error(f"[{cog.name}] Failed to register cog: {str(e)}", exc_info=True)
        raise
