import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class GeminiProCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Gemini-Pro",
            nickname="GeminiP",
            trigger_words=['geminipro', 'geminip', 'gemini pro 1.5', 'freezy'],
            model="google/gemini-pro-1.5",
            provider="openrouter",
            prompt_file="geminipro",
            supports_vision=True
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Gemini-Pro] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Gemini-Pro] Using provider: {self.provider}")
        logging.debug(f"[Gemini-Pro] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Gemini-Pro"

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
            logging.debug(f"[Gemini-Pro] Triggered by message: {message.content}")
            async with message.channel.typing():
                try:
                    # Process message and get response
                    logging.debug(f"[Gemini-Pro] Processing message with provider: {self.provider}, model: {self.model}")
                    response = await self.generate_response(message)
                    
                    if response:
                        logging.debug(f"[Gemini-Pro] Got response: {response[:100]}...")
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
                            logging.debug(f"[Gemini-Pro] Logged interaction for user {message.author.id}")

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
                            logging.error(f"[Gemini-Pro] Failed to log interaction: {str(e)}", exc_info=True)
                    else:
                        logging.error("[Gemini-Pro] No response received from API")
                        await message.add_reaction('❌')
                        await message.reply(f"[{self.name}] Failed to generate a response. Please try again.")

                except Exception as e:
                    logging.error(f"[Gemini-Pro] Error in message handling: {str(e)}", exc_info=True)
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
        cog = GeminiProCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Gemini-Pro] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Gemini-Pro] Failed to register cog: {str(e)}", exc_info=True)
        raise
