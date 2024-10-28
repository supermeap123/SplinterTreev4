import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class NemotronCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Nemotron",
            nickname="Nemotron",
            trigger_words=['nemotron', 'nvidia'],
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            provider="openrouter",
            prompt_file="nemotron",
            supports_vision=False
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Nemotron] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Nemotron] Using provider: {self.provider}")
        logging.debug(f"[Nemotron] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Nemotron"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        msg_content = message.content.lower()
        is_triggered = any(word in msg_content for word in self.trigger_words)

        # Add message to context before processing
        if self.context_cog:
            channel_id = str(message.channel.id)
            guild_id = str(message.guild.id) if message.guild else None
            user_id = str(message.author.id)
            content = message.content
            is_assistant = False
            persona_name = self.name
            emotion = None

            await self.context_cog.add_message_to_context(channel_id, guild_id, user_id, content, is_assistant, persona_name, emotion)

        if is_triggered:
            logging.debug(f"[Nemotron] Triggered by message: {message.content}")
            async with message.channel.typing():
                try:
                    # Process message and get response
                    logging.debug(f"[Nemotron] Processing message with provider: {self.provider}, model: {self.model}")
                    response = await self.generate_response(message)
                    
                    if response:
                        logging.debug(f"[Nemotron] Got response: {response[:100]}...")
                        # Handle the response and get emotion
                        emotion = await self.handle_response(response, message)
                        
                        # Log interaction
                        try:
                            log_interaction(
                                user_id=message.author.id,
                                guild_id=message.guild.id if message.guild else None,
                                persona_name=self.name,
                                user_message=message.content,
                                assistant_reply=response,
                                emotion=emotion
                            )
                            logging.debug(f"[Nemotron] Logged interaction for user {message.author.id}")

                            # Add bot's response to context
                            if self.context_cog:
                                await self.context_cog.add_message_to_context(
                                    channel_id=str(message.channel.id),
                                    guild_id=str(message.guild.id) if message.guild else None,
                                    user_id=str(self.bot.user.id),
                                    content=response,
                                    is_assistant=True,
                                    persona_name=self.name,
                                    emotion=emotion
                                )
                        except Exception as e:
                            logging.error(f"[Nemotron] Failed to log interaction: {str(e)}", exc_info=True)
                    else:
                        logging.error("[Nemotron] No response received from API")
                        await message.add_reaction('❌')
                        await message.reply(f"[{self.name}] Failed to generate a response. Please try again.")

                except Exception as e:
                    logging.error(f"[Nemotron] Error in message handling: {str(e)}", exc_info=True)
                    await message.add_reaction('❌')
                    error_msg = str(e)
                    if "insufficient_quota" in error_msg.lower():
                        await message.reply("⚠️ API quota exceeded. Please try again later.")
                    elif "invalid_api_key" in error_msg.lower():
                        await message.reply("🔑 API configuration error. Please contact the bot administrator.")
                    elif "rate_limit_exceeded" in error_msg.lower():
                        await message.reply("⏳ Rate limit exceeded. Please try again later.")
                    else:
                        await message.reply(f"[{self.name}] An error occurred while processing your request.")

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = NemotronCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Nemotron] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Nemotron] Failed to register cog: {str(e)}", exc_info=True)
        raise
