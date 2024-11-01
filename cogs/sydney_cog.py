import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion
import time

class SydneyCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Sydney",
            nickname="Sydney", 
            trigger_words=['sydney', 'syd', 'mama kunty'],
            model="openpipe:Sydney-Court",
            provider="openpipe",
            prompt_file="sydney_prompts",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Sydney] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Sydney] Using provider: {self.provider}")
        logging.debug(f"[Sydney] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Sydney"

    async def generate_response(self, message):
        """Generate a response using OpenPipe"""
        try:
            # Format system prompt
            formatted_prompt = self.format_system_prompt(message)
            messages = [{"role": "system", "content": formatted_prompt}]

            # Get last 50 messages from database
            channel_id = str(message.channel.id)
            history_messages = await self.context_cog.get_context_messages(channel_id, limit=50)
            messages.extend(history_messages)

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

            logging.debug(f"[Sydney] Sending {len(messages)} messages to API")
            logging.debug(f"[Sydney] Formatted prompt: {formatted_prompt}")

            # Get temperature for this agent
            temperature = self.get_temperature(self.name)
            logging.debug(f"[Sydney] Using temperature: {temperature}")

            # Prepare request payload
            req_payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }

            # Record start time
            requested_at = int(time.time() * 1000)

            # Call OpenPipe API
            response_data = await self.api_client.call_openpipe(**req_payload)

            # Record end time
            received_at = int(time.time() * 1000)

            # Prepare response payload (this will be a generator for streaming responses)
            resp_payload = {
                "choices": [{
                    "message": {
                        "content": "Streaming response completed"
                    }
                }]
            }

            # Report to OpenPipe
            await self.api_client.openpipe_client.report(
                requested_at=requested_at,
                received_at=received_at,
                req_payload=req_payload,
                resp_payload=resp_payload,
                status_code=200,
                metadata={"prompt_id": str(message.id)}
            )

            return response_data

        except Exception as e:
            logging.error(f"Error processing message for Sydney: {str(e)}")
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

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
                logging.error(f"[Sydney] Failed to add message to context: {str(e)}")

        # Let base_cog handle message processing
        await super().handle_message(message)

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = SydneyCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Sydney] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Sydney] Failed to register cog: {str(e)}", exc_info=True)
        raise
