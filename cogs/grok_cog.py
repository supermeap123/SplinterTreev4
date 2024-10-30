import discord
from discord.ext import commands
import logging
from .base_cog import BaseCog

class GrokBetaCog(BaseCog):  # Changed class name to match qualified_name
    def __init__(self, bot):
        super().__init__(
            bot=bot,
            name="Grok-Beta",
            nickname="Grok",
            trigger_words=['grok', 'grok beta', 'xai'],
            model="x-ai/grok-beta",
            provider="openrouter",
            prompt_file="grok",
            supports_vision=False  # Disable vision support for now to focus on core functionality
        )
        self.context_cog = bot.get_cog('ContextCog')
        logging.debug(f"[Grok-Beta] Initialized with raw_prompt: {self.raw_prompt}")
        logging.debug(f"[Grok-Beta] Using provider: {self.provider}")
        logging.debug(f"[Grok-Beta] Trigger words: {self.trigger_words}")

    @property
    def qualified_name(self):
        """Override qualified_name to match the expected cog name"""
        return "Grok-Beta"

    async def handle_message(self, message):
        """Override handle_message to ensure proper async flow"""
        if message.author == self.bot.user:
            return

        logging.debug(f"[Grok-Beta] Received message: {message.content}")
        logging.debug(f"[Grok-Beta] Message author: {message.author}")

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
                logging.error(f"[Grok-Beta] Failed to add message to context: {str(e)}")

        # Continue with normal message processing
        await super().handle_message(message)

async def setup(bot):
    # Register the cog with its proper name
    try:
        logging.info("[Grok-Beta] Starting cog setup...")
        cog = GrokBetaCog(bot)  # Updated to use new class name
        await bot.add_cog(cog)
        logging.info(f"[Grok-Beta] Registered cog with qualified_name: {cog.qualified_name}")
        logging.info(f"[Grok-Beta] Cog is loaded and listening for triggers: {cog.trigger_words}")
        return cog
    except Exception as e:
        logging.error(f"[Grok-Beta] Failed to register cog: {str(e)}", exc_info=True)
        raise
