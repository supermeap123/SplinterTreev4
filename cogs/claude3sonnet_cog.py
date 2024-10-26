import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class Claude3SonnetCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Claude-3.5-Sonnet",
            nickname="Sonnet",
            trigger_words=['sonnet', 'claude 3.5', 'claude3.5', 'claude-3.5-sonnet', 'claude3sonnet'],
            model="anthropic/claude-3-sonnet:beta",
            provider="openrouter",
            prompt_file="claude3sonnet",
            supports_vision=True
        )
        logging.debug(f"[Claude-3.5-Sonnet] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Claude-3.5-Sonnet] Using provider: {self.provider}")
        logging.debug(f"[Claude-3.5-Sonnet] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Claude-3.5-Sonnet"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        msg_content = message.content.lower()
        is_triggered = any(word in msg_content for word in self.trigger_words)

        if is_triggered:
            logging.debug(f"[Claude-3.5-Sonnet] Triggered by message: {message.content}")
            async with message.channel.typing():
                try:
                    # Process message and get response
                    logging.debug(f"[Claude-3.5-Sonnet] Processing message with provider: {self.provider}, model: {self.model}")
                    response = await self.generate_response(message)
                    
                    if response:
                        logging.debug(f"[Claude-3.5-Sonnet] Got response: {response[:100]}...")
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
                            logging.debug(f"[Claude-3.5-Sonnet] Logged interaction for user {message.author.id}")
                        except Exception as e:
                            logging.error(f"[Claude-3.5-Sonnet] Failed to log interaction: {str(e)}", exc_info=True)
                    else:
                        logging.error("[Claude-3.5-Sonnet] No response received from API")
                        await message.add_reaction('❌')
                        await message.reply(f"[{self.name}] Failed to generate a response. Please try again.")

                except Exception as e:
                    logging.error(f"[Claude-3.5-Sonnet] Error in message handling: {str(e)}", exc_info=True)
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
        cog = Claude3SonnetCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Claude-3.5-Sonnet] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Claude-3.5-Sonnet] Failed to register cog: {str(e)}", exc_info=True)
        raise
