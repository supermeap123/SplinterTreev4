import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
import json

class FreeRouterCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="FreeRouter",
            nickname="FreeRouter",
            trigger_words=["*"],  # Match all messages
            model="openpipe:FreeRouter-v3-726",
            provider="openpipe",
            prompt_file="freerouter_prompts",
            supports_vision=False
        )
        logging.debug(f"[FreeRouter] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[FreeRouter] Using provider: {self.provider}")
        logging.debug(f"[FreeRouter] Vision support: {self.supports_vision}")

        # Load temperature settings
        try:
            with open('temperatures.json', 'r') as f:
                self.temperatures = json.load(f)
        except Exception as e:
            logging.error(f"[FreeRouter] Failed to load temperatures.json: {e}")
            self.temperatures = {}

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "FreeRouter"

    def get_temperature(self):
        """Get temperature setting for this agent"""
        return self.temperatures.get(self.name.lower(), 0.7)

    async def handle_message(self, message, full_content=None):
        """Handle incoming messages for routing"""
        try:
            # Skip if message is from this bot
            if message.author == self.bot.user:
                return

            # Skip if message is a command
            if message.content.startswith('!'):
                return

            # Use full_content if provided, otherwise use message content
            content = full_content or message.content

            # Generate response stream
            response_stream = await self.generate_response(message)

            if response_stream:
                # Send response as a stream
                response_message = await message.reply(f"[FreeRouter] Processing...")
                full_response = ""
                async for chunk in response_stream:
                    if chunk:
                        full_response += chunk
                        # Update message with current response
                        await response_message.edit(content=f"[FreeRouter] {full_response}")

                # Final edit to remove processing indicator
                await response_message.edit(content=f"[FreeRouter] {full_response}")
            else:
                await message.reply("[FreeRouter] Unable to generate a response.")

        except Exception as e:
            logging.error(f"[FreeRouter] Error in handle_message: {e}")
            await message.reply(f"[FreeRouter] An error occurred: {str(e)}")

    async def generate_response(self, message):
        """Generate a response using openrouter"""
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

            logging.debug(f"[FreeRouter] Sending {len(messages)} messages to API")
            logging.debug(f"[FreeRouter] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature()
            logging.debug(f"[FreeRouter] Using temperature: {temperature}")

            # Get user_id and guild_id
            user_id = str(message.author.id)
            guild_id = str(message.guild.id) if message.guild else None

            # Call API and return the stream directly
            response_stream = await self.api_client.call_openpipe(
                messages=messages,
                model=self.model,
                temperature=temperature,
                stream=True,
                provider="openpipe",
                user_id=user_id,
                guild_id=guild_id,
                prompt_file="freerouter_prompts"
            )

            return response_stream

        except Exception as e:
            logging.error(f"Error processing message for FreeRouter: {e}")
            return None

async def setup(bot):
    try:
        cog = FreeRouterCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[FreeRouter] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[FreeRouter] Failed to register cog: {e}", exc_info=True)
        raise
