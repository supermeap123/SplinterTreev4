import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog
from shared.utils import log_interaction, analyze_emotion

class SonarCog(BaseCog):
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Sonar",
            nickname="Sonar",
            trigger_words=['sonar', 'sonar ai'],
            model="perplexity/llama-3.1-sonar-huge-128k-online",
            provider="openrouter",
            prompt_file="sonar",
            supports_vision=False
        )
        logging.debug(f"[Sonar] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Sonar] Using provider: {self.provider}")
        logging.debug(f"[Sonar] Vision support: {self.supports_vision}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Sonar"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return

        # Check if message triggers this cog
        msg_content = message.content.lower()
        is_triggered = any(word in msg_content for word in self.trigger_words)

        if is_triggered:
            logging.debug(f"[Sonar] Triggered by message: {message.content}")
            async with message.channel.typing():
                try:
                    # Process message and get response
                    logging.debug(f"[Sonar] Processing message with provider: {self.provider}, model: {self.model}")
                    response, emotion = await self.handle_message(message)
                    
                    if response:
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
                            logging.debug(f"[Sonar] Logged interaction for user {message.author.id}")
                        except Exception as e:
                            logging.error(f"[Sonar] Failed to log interaction: {str(e)}", exc_info=True)

                except Exception as e:
                    logging.error(f"[Sonar] Error in message handling: {str(e)}", exc_info=True)

async def setup(bot):
    # Register the cog with its proper name
    try:
        cog = SonarCog(bot)
        await bot.add_cog(cog)
        logging.info(f"[Sonar] Registered cog with qualified_name: {cog.qualified_name}")
        return cog
    except Exception as e:
        logging.error(f"[Sonar] Failed to register cog: {str(e)}", exc_info=True)
        raise
