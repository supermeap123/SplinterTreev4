import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class Claude1_1Cog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-1.1",
            nickname="Claude",
            trigger_words=['claude 1', 'claude1', 'claude 1.1'],
            model="anthropic/claude-instant-1.1",  # Fixed model name
            provider="openrouter",
            prompt_file="claude1_1",
            supports_vision=False
        )
        logging.debug(f"[Claude-1.1] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Claude-1.1] Using provider: {self.provider}")
        logging.debug(f"[Claude-1.1] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Claude-1.1"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        msg_content = message.content.lower()
        is_triggered = any(word in msg_content for word in self.trigger_words)

        if is_triggered:
            logging.debug(f"[Claude-1.1] Triggered by message: {message.content}")
            async with message.channel.typing():
                try:
                    # Process message and get response
                    logging.debug(f"[Claude-1.1] Processing message with provider: {self.provider}, model: {self.model}")
                    response = await self.generate_response(message)
                    
                    if response:
                        logging.debug(f"[Claude-1.1] Got response: {response[:100]}...")
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
                            logging.debug(f"[Claude-1.1] Logged interaction for user {message.author.id}")
                        except Exception as e:
                            logging.error(f"[Claude-1.1] Failed to log interaction: {str(e)}", exc_info=True)
                    else:
                        logging.error("[Claude-1.1] No response received from API")
                        await message.add_reaction('❌')
                        await message.reply(f"[{self.name}] Failed to generate a response. Please try again.")

                except Exception as e:
                    logging.error(f"[Claude-1.1] Error in message handling: {str(e)}", exc_info=True)
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
        cog = Claude1_1Cog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Claude-1.1] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-1.1] Failed to register cog: {str(e)}", exc_info=True)
        raise
