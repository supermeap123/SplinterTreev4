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
            nickname="Gemini",
            trigger_words=['gemini', 'gemini pro'],
            model="google/gemini-pro-1.5",  # Keeping the model line as instructed
            provider="openrouter",  # Updating the provider as per the instructions
            prompt_file="geminipro",
            supports_vision=False
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
                logging.error(f"[Gemini-Pro] Failed to add message to context: {str(e)}")

        # Let base_cog handle image processing first
        await super().handle_message(message)

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
